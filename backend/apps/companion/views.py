"""
Endpoints DRF publics du module Companion.

Toutes les vues acceptent un `public_id` voyageur (slug 24 chars,
généré aléatoirement à l'enregistrement). Pas de JWT côté PWA voyageur.

Convention de rate-limiting (configurée dans settings) :
- companion_checkin :   12/heure
- companion_location :  60/heure (ping volontaire)
- companion_consent :   30/heure
- companion_push :      30/heure
"""
from __future__ import annotations

from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.travelers.models import Traveler

from . import services
from .models import (
    ConsentScope,
    LocationEventType,
    PushSubscription,
    PushSubscriptionDevice,
)
from .serializers import (
    CheckinSerializer,
    ConsentRecordSerializer,
    LocationPingSerializer,
    PushSubscribeSerializer,
    PushUnsubscribeSerializer,
)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def _client_ip(request) -> str | None:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_traveler(public_id: str) -> Traveler:
    return get_object_or_404(Traveler, public_id=public_id)


def _get_active_quarantine(traveler):
    """Récupère la quarantaine active (ou la plus récente) du voyageur,
    pour y rattacher un DailyCheck. Retourne None si aucune."""
    return (
        traveler.quarantines.filter(status__in=["ACTIVE", "EXTENDED"])
        .order_by("-started_on")
        .first()
        or traveler.quarantines.order_by("-started_on").first()
    )


# ----------------------------------------------------------------------------
# Consentement
# ----------------------------------------------------------------------------


class ConsentView(APIView):
    """Enregistre (ou retire) un consentement explicite.

    POST /api/v1/public/consent/
    Body : { public_id, scope, granted, consent_version, text_excerpt, revocation_reason }
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_consent"

    def post(self, request):
        ser = ConsentRecordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        traveler = _get_traveler(ser.validated_data["public_id"])

        consent = services.record_consent(
            traveler=traveler,
            scope=ser.validated_data["scope"],
            granted=bool(ser.validated_data["granted"]),
            version=ser.validated_data.get("consent_version", "v1"),
            text_excerpt=ser.validated_data.get("text_excerpt", ""),
            ip=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            revocation_reason=ser.validated_data.get("revocation_reason", ""),
        )
        return Response({
            "consent_id": consent.uuid,
            "scope": consent.scope,
            "granted": consent.granted,
            "granted_at": consent.granted_at,
            "consent_version": consent.consent_version,
        }, status=status.HTTP_201_CREATED)


# ----------------------------------------------------------------------------
# Check-in quotidien
# ----------------------------------------------------------------------------


class CheckinView(APIView):
    """Réception d'un check-in sanitaire quotidien.

    POST /api/v1/public/checkin/
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_checkin"

    def post(self, request):
        ser = CheckinSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        traveler = _get_traveler(data["public_id"])

        # 1. Créer le DailyCheck dans apps.quarantine (logique métier déjà
        #    existante : day_index, alert_raised, etc.)
        from apps.quarantine.models import DailyCheck
        quarantine = _get_active_quarantine(traveler)
        symptoms = data.get("symptoms") or {}
        has_symptoms = any(bool(v) for v in symptoms.values())
        feeling = data.get("feeling", "ok")
        needs_assistance = feeling == "assistance" or bool(data.get("needs_contact"))

        check = None
        if quarantine:
            day_index = max(0, (date.today() - quarantine.started_on).days)
            # Idempotent : un seul check par jour
            check, created = DailyCheck.objects.update_or_create(
                quarantine=quarantine,
                day_index=day_index,
                defaults={
                    "check_date": date.today(),
                    "temperature_celsius": data.get("temperature_celsius"),
                    "has_symptoms": has_symptoms,
                    "symptoms_details": {**symptoms, "feeling": feeling,
                                          "needs_contact": bool(data.get("needs_contact"))},
                    "is_self_reported": True,
                    "notes": data.get("notes", ""),
                },
            )

        # 2. Si position fournie + consentement → enregistrer ping
        location = None
        if data.get("latitude") is not None and data.get("longitude") is not None:
            event_type = (
                LocationEventType.ASSISTANCE_REQUEST if needs_assistance
                else LocationEventType.SYMPTOM_REPORT if has_symptoms
                else LocationEventType.DAILY_CHECKIN
            )
            location = services.record_location_ping(
                traveler=traveler,
                latitude=float(data["latitude"]),
                longitude=float(data["longitude"]),
                accuracy_m=data.get("accuracy_m"),
                event_type=event_type,
                device_info=request.META.get("HTTP_USER_AGENT", "")[:200],
            )

        # 3. Déclencher une HealthAlert si symptômes critiques
        alert = services.raise_alert_from_checkin(
            traveler=traveler,
            symptoms=symptoms,
            location=location,
            needs_assistance=needs_assistance,
        )
        if alert and check is not None:
            check.alert_raised = True
            check.save(update_fields=["alert_raised"])

        # 4. Message rassurant adapté
        if needs_assistance:
            message = (
                "Merci. Une équipe sanitaire pourra prendre contact avec vous très bientôt. "
                "En cas d'urgence, composez le 143 (Allô Santé) ou le 185 (SAMU)."
            )
        elif alert and alert.severity in ("HIGH", "CRITICAL"):
            message = (
                "Merci pour votre signalement. Une équipe sanitaire pourra vous orienter "
                "calmement vers la conduite à tenir. En cas de doute, composez le 143."
            )
        elif has_symptoms:
            message = (
                "Merci pour votre signalement. Reposez-vous, hydratez-vous, et n'hésitez "
                "pas à nous prévenir si votre état évolue."
            )
        else:
            message = "Merci d'avoir pris ce moment pour nous donner de vos nouvelles. Bonne journée !"

        return Response({
            "ok": True,
            "message": message,
            "alert_created": bool(alert),
            "alert_severity": alert.severity if alert else None,
            "location_recorded": bool(location),
        }, status=status.HTTP_201_CREATED)


# ----------------------------------------------------------------------------
# Géolocalisation
# ----------------------------------------------------------------------------


class LocationPingView(APIView):
    """Ping de position volontaire (bouton dédié dans la PWA).

    POST /api/v1/public/location/ping/
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_location"

    def post(self, request):
        ser = LocationPingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        traveler = _get_traveler(data["public_id"])

        ping = services.record_location_ping(
            traveler=traveler,
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            accuracy_m=data.get("accuracy_m"),
            altitude_m=data.get("altitude_m"),
            speed_mps=data.get("speed_mps"),
            heading_deg=data.get("heading_deg"),
            event_type=data.get("event_type", LocationEventType.MANUAL_SHARE),
            device_info=data.get("device_info") or request.META.get("HTTP_USER_AGENT", "")[:200],
        )
        if ping is None:
            return Response(
                {"ok": False, "reason": "consent_required",
                 "message": "Veuillez d'abord autoriser le partage de votre position dans la PWA."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({
            "ok": True,
            "ping_id": ping.uuid,
            "captured_at": ping.captured_at,
            "message": "Position partagée — merci. L'INHP pourra vous orienter plus rapidement si besoin.",
        }, status=status.HTTP_201_CREATED)


# ----------------------------------------------------------------------------
# Statut de suivi (status board PWA)
# ----------------------------------------------------------------------------


class FollowUpStatusView(APIView):
    """Snapshot de la situation actuelle du voyageur pour la PWA.

    GET /api/v1/public/follow-up/status/?public_id=TRV-XXXX

    Renvoie tout ce qu'il faut pour afficher la page /voyageur/suivi :
    - dates de surveillance (début, jour J, fin) ;
    - dernier check-in (date + état) ;
    - consentements actifs ;
    - assistance phones.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_consent"

    def get(self, request):
        public_id = request.query_params.get("public_id", "")
        if not public_id:
            return Response({"detail": "public_id requis."}, status=400)
        traveler = _get_traveler(public_id)
        quarantine = _get_active_quarantine(traveler)

        last_check = None
        day_index = None
        if quarantine:
            check_obj = quarantine.daily_checks.order_by("-check_date").first()
            if check_obj:
                last_check = {
                    "check_date": check_obj.check_date,
                    "has_symptoms": check_obj.has_symptoms,
                    "temperature_celsius": (
                        float(check_obj.temperature_celsius)
                        if check_obj.temperature_celsius is not None else None
                    ),
                    "feeling": (check_obj.symptoms_details or {}).get("feeling"),
                }
            day_index = max(0, (date.today() - quarantine.started_on).days)

        # Consentements actifs (un par scope)
        consents: dict = {}
        for scope_value, _label in ConsentScope.choices:
            consents[scope_value] = services.has_consent(traveler, scope_value)

        return Response({
            "traveler": {
                "public_id": traveler.public_id,
                "full_name": traveler.full_name,
            },
            "quarantine": {
                "active": bool(quarantine),
                "started_on": quarantine.started_on if quarantine else None,
                "expected_end_on": quarantine.expected_end_on if quarantine else None,
                "day_index": day_index,
                "total_days": (
                    (quarantine.expected_end_on - quarantine.started_on).days
                    if quarantine else None
                ),
            },
            "last_check": last_check,
            "consents": consents,
            "assistance": {
                "samu": "185",
                "allo_sante": "143",
                "secours": "101",
            },
        })


# ----------------------------------------------------------------------------
# Push subscriptions
# ----------------------------------------------------------------------------


class MyDataSummaryView(APIView):
    """Résumé self-service des données du voyageur (right of access soft).

    GET /api/v1/public/me/data-summary/?public_id=TRV-XXXX

    Renvoie :
    - consentements actifs/historique (nombre par scope) ;
    - nombres de check-ins, pings, alertes (sans contenu) ;
    - dernière mise à jour ;
    - lien vers l'export complet.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_consent"

    def get(self, request):
        public_id = request.query_params.get("public_id", "")
        if not public_id:
            return Response({"detail": "public_id requis."}, status=400)
        traveler = _get_traveler(public_id)

        # Consentements résumés
        consents_summary = []
        for scope_value, scope_label in ConsentScope.choices:
            qs = traveler.privacy_consents.filter(scope=scope_value).order_by("-granted_at")
            last = qs.first()
            consents_summary.append({
                "scope": scope_value,
                "label": str(scope_label),
                "granted": services.has_consent(traveler, scope_value),
                "last_decision_at": last.granted_at if last else None,
                "history_count": qs.count(),
            })

        return Response({
            "traveler": {
                "public_id": traveler.public_id,
                "full_name": traveler.full_name,
                "registered_at": traveler.created_at,
            },
            "consents": consents_summary,
            "counters": {
                "checkins": sum(q.daily_checks.count() for q in traveler.quarantines.all()),
                "location_pings": traveler.location_pings.count(),
                "push_subscriptions_active": traveler.push_subscriptions.filter(is_active=True).count(),
            },
        })


class MyDataExportView(APIView):
    """Export JSON complet — RGPD right of access (loi 2013-450 art. 32).

    GET /api/v1/public/me/export/?public_id=TRV-XXXX

    Retourne TOUTES les données stockées sur le voyageur dans
    le périmètre du module companion (et un résumé identité venant
    de Traveler). Téléchargeable directement par le voyageur.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_consent"

    def get(self, request):
        from django.http import HttpResponse
        import json
        public_id = request.query_params.get("public_id", "")
        if not public_id:
            return Response({"detail": "public_id requis."}, status=400)
        traveler = _get_traveler(public_id)

        # Note : on n'expose PAS la liste des agents qui ont consulté
        # les données via cet endpoint public (sensible). Le voyageur doit
        # passer par une demande formelle écrite (email DPO).
        payload = {
            "traveler": {
                "public_id": traveler.public_id,
                "full_name": traveler.full_name,
                "phone": traveler.phone_mobile,
                "email": traveler.email,
                "nationality": traveler.nationality.code if traveler.nationality else None,
                "registered_at": traveler.created_at.isoformat(),
                "current_health_status": traveler.current_health_status,
            },
            "consents": [
                {
                    "scope": c.scope, "granted": c.granted,
                    "version": c.consent_version,
                    "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                    "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                    "revocation_reason": c.revocation_reason,
                }
                for c in traveler.privacy_consents.order_by("granted_at")
            ],
            "location_pings": [
                {
                    "latitude": float(p.latitude), "longitude": float(p.longitude),
                    "accuracy_m": p.accuracy_m,
                    "event_type": p.event_type, "source": p.source,
                    "captured_at": p.captured_at.isoformat(),
                    "consent_version": p.consent_version,
                }
                for p in traveler.location_pings.order_by("captured_at")
            ],
            "daily_checks": [
                {
                    "check_date": str(check.check_date),
                    "day_index": check.day_index,
                    "temperature_celsius": (
                        float(check.temperature_celsius)
                        if check.temperature_celsius is not None else None
                    ),
                    "has_symptoms": check.has_symptoms,
                    "symptoms_details": check.symptoms_details,
                    "is_self_reported": check.is_self_reported,
                }
                for q in traveler.quarantines.all()
                for check in q.daily_checks.order_by("check_date")
            ],
            "push_subscriptions": [
                {
                    "device_type": s.device_type, "locale": s.locale,
                    "is_active": s.is_active,
                    "created_at": s.created_at.isoformat(),
                    "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
                }
                for s in traveler.push_subscriptions.all()
            ],
            "exported_at": timezone.now().isoformat(),
        }
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        resp = HttpResponse(body, content_type="application/json")
        resp["Content-Disposition"] = (
            f'attachment; filename="epitrace-mes-donnees-{traveler.public_id}.json"'
        )
        return resp


class PushPublicKeyView(APIView):
    """Expose la clé publique VAPID en base64url pour la PWA.

    GET /api/v1/public/push/public-key/

    Réponse : { "public_key": "BLF...", "applicationServerKey": "BLF..." }
    """

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            from .push import get_vapid_public_key_b64url
            key = get_vapid_public_key_b64url()
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=503)
        return Response({"public_key": key, "applicationServerKey": key})


class PushSubscribeView(APIView):
    """Enregistre un abonnement Web Push (VAPID).

    POST /api/v1/public/push/subscribe/
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_push"

    def post(self, request):
        ser = PushSubscribeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        traveler = _get_traveler(data["public_id"])

        sub = data["subscription"]
        endpoint = sub["endpoint"]
        keys = sub["keys"]

        # Vérification du consentement push
        if not services.has_consent(traveler, ConsentScope.PUSH_NOTIFICATIONS):
            return Response(
                {"ok": False, "reason": "consent_required",
                 "message": "Veuillez d'abord accepter de recevoir les rappels sanitaires."},
                status=status.HTTP_403_FORBIDDEN,
            )

        device = (data.get("device_type") or "unknown").lower()
        if device not in dict(PushSubscriptionDevice.choices):
            device = PushSubscriptionDevice.UNKNOWN

        obj, _created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "traveler": traveler,
                "p256dh": keys["p256dh"],
                "auth": keys["auth"],
                "user_agent": (data.get("user_agent") or request.META.get("HTTP_USER_AGENT", ""))[:300],
                "device_type": device,
                "locale": data.get("locale", "")[:10],
                "is_active": True,
                "failure_count": 0,
            },
        )
        return Response({
            "ok": True,
            "subscription_id": obj.uuid,
            "is_active": obj.is_active,
        }, status=status.HTTP_201_CREATED)


class PushUnsubscribeView(APIView):
    """Désabonne un endpoint push (sur action voyageur ou nettoyage).

    POST /api/v1/public/push/unsubscribe/
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "companion_push"

    def post(self, request):
        ser = PushUnsubscribeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        traveler = _get_traveler(data["public_id"])
        n = PushSubscription.objects.filter(
            traveler=traveler, endpoint=data["endpoint"], is_active=True,
        ).update(is_active=False, updated_at=timezone.now())
        return Response({"ok": True, "unsubscribed": n})
