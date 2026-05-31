"""Vues admin du module notifications + webhooks fournisseurs."""
from __future__ import annotations

import hmac
import logging
from hashlib import sha1
from base64 import b64encode

from django.conf import settings
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView


# ---------------------------------------------------------------------------
# Anti-spam : 30 envois manuels par heure et par agent
# Distinct de rates globaux DRF — défini ici pour isoler les notifications.
# ---------------------------------------------------------------------------
class SendNotificationThrottle(UserRateThrottle):
    scope = "notifications_send"
    rate = "30/hour"

from apps.travelers.models import Traveler

from .models import (
    Notification, NotificationStatus, NotificationTemplate, Provider,
)
from .permissions import (
    CanRetryNotification, CanSendNotification, CanViewNotifications,
)
from .serializers import (
    NotificationSerializer, NotificationTemplateSerializer,
    SendNotificationSerializer,
)
from .services.audit import Actions, log_action
from .services.dispatcher import (
    send_manual_message, send_template_message,
)
from .services.router import (
    NotificationProviderRouter, PhoneValidationError,
)

logger = logging.getLogger("epidemitracker.notifications.views")


# ---------------------------------------------------------------------------
# Templates — lecture pour tous, écriture pour rôles admin
# ---------------------------------------------------------------------------
class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.select_related("disease", "created_by").all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active", "disease"]
    search_fields = ["code", "name", "description"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ---------------------------------------------------------------------------
# Notification (historique) — lecture + actions (retry / cancel)
# ---------------------------------------------------------------------------
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        Notification.objects
        .select_related("template", "traveler", "sent_by")
        .order_by("-created_at")
    )
    serializer_class = NotificationSerializer
    permission_classes = [CanViewNotifications]
    filterset_fields = [
        "channel", "status", "provider", "message_type", "direction",
        "traveler", "template",
    ]
    search_fields = ["recipient", "normalized_phone", "body", "subject"]

    @action(
        detail=False, methods=["post"], url_path="send",
        permission_classes=[CanSendNotification],
        throttle_classes=[SendNotificationThrottle],
    )
    def send_now(self, request):
        """POST /api/v1/notifications/send/ — envoi manuel depuis le dashboard."""
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        traveler = None
        recipient = (data.get("recipient") or "").strip()
        if data.get("traveler"):
            traveler = Traveler.objects.filter(pk=data["traveler"]).first()
            if not traveler:
                return Response({"detail": "Voyageur introuvable."}, status=404)
            if not recipient:
                recipient = (
                    getattr(traveler, "whatsapp_phone", "") or
                    traveler.phone_mobile or
                    getattr(traveler, "emergency_phone_ci", "") or ""
                ).strip()

        if not recipient:
            return Response({"detail": "Aucun numéro de destinataire disponible."}, status=400)

        # Pré-validation pour retour 400 propre
        try:
            NotificationProviderRouter.detect(recipient, channel=data["channel"])
        except PhoneValidationError as exc:
            return Response({"detail": str(exc)}, status=400)

        if data.get("template_code"):
            result = send_template_message(
                traveler=traveler, recipient=recipient,
                template_code=data["template_code"],
                context=data.get("context") or {},
                channel=data["channel"],
                sent_by=request.user, request=request,
            )
        else:
            result = send_manual_message(
                traveler=traveler, recipient=recipient,
                body=data["body"],
                channel=data["channel"],
                sent_by=request.user, request=request,
            )

        if not result.ok:
            return Response({"detail": result.error}, status=400)

        notif = Notification.objects.get(pk=result.notification_id)
        return Response(NotificationSerializer(notif).data, status=201)

    @action(detail=False, methods=["post"], url_path="preview-routing",
            permission_classes=[CanSendNotification])
    def preview_routing(self, request):
        """POST /api/v1/notifications/preview-routing/ — pré-affichage du provider."""
        phone = (request.data.get("phone") or "").strip()
        channel = (request.data.get("channel") or "sms").lower()
        try:
            decision = NotificationProviderRouter.detect(phone, channel=channel)
        except PhoneValidationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({
            "normalized": decision.normalized,
            "country_code": decision.country_code,
            "provider": decision.provider,
            "is_ivoirian": decision.is_ivoirian,
        })

    @action(detail=True, methods=["post"], permission_classes=[CanRetryNotification])
    def retry(self, request, pk=None):
        """Relance manuellement une notification FAILED ou CANCELLED."""
        notif = self.get_object()
        if notif.status not in (NotificationStatus.FAILED, NotificationStatus.CANCELLED):
            return Response(
                {"detail": "Seules les notifications FAILED ou CANCELLED peuvent être relancées."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notif.status = NotificationStatus.QUEUED
        notif.error_message = ""
        notif.queued_at = timezone.now()
        notif.save(update_fields=["status", "error_message", "queued_at", "updated_at"])

        log_action(
            notification=notif, action=Actions.RETRY,
            actor=request.user, request=request,
            metadata={"manual_retry": True},
        )

        from .tasks import send_notification_task
        send_notification_task.delay(notif.id)
        return Response(NotificationSerializer(notif).data)

    @action(
        detail=False, methods=["post"], url_path="bulk-retry",
        permission_classes=[CanRetryNotification],
    )
    def bulk_retry(self, request):
        """POST /api/v1/notifications/bulk-retry/ — relance en lot.

        Body : {"ids": [1, 2, 3]} ou {"all_failed": true} pour relancer
        toutes les notifications FAILED des dernières 24h.
        Retourne le nombre de notifs effectivement re-queuées + détails.
        """
        ids = request.data.get("ids") or []
        all_failed = bool(request.data.get("all_failed"))
        max_age_hours = int(request.data.get("max_age_hours") or 24)

        if not ids and not all_failed:
            return Response(
                {"detail": "Fournir 'ids' (liste) ou 'all_failed': true."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build queryset : par IDs explicites OU tous les FAILED récents.
        qs = Notification.objects.filter(
            status__in=(NotificationStatus.FAILED, NotificationStatus.CANCELLED),
        )
        if ids:
            try:
                ids_int = [int(i) for i in ids][:500]  # cap de sécurité
            except (ValueError, TypeError):
                return Response({"detail": "IDs invalides."}, status=400)
            qs = qs.filter(pk__in=ids_int)
        elif all_failed:
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(hours=max_age_hours)
            qs = qs.filter(failed_at__gte=cutoff)[:500]

        requeued = 0
        results = []
        from .tasks import send_notification_task
        for notif in qs:
            notif.status = NotificationStatus.QUEUED
            notif.error_message = ""
            notif.queued_at = timezone.now()
            notif.save(update_fields=["status", "error_message", "queued_at", "updated_at"])
            log_action(
                notification=notif, action=Actions.RETRY,
                actor=request.user, request=request,
                metadata={"manual_retry": True, "bulk": True},
            )
            send_notification_task.delay(notif.id)
            requeued += 1
            results.append({"id": notif.id, "recipient": notif.masked_recipient})

        return Response({
            "ok": True,
            "requeued": requeued,
            "results": results,
        })

    @action(detail=True, methods=["post"], permission_classes=[CanRetryNotification])
    def cancel(self, request, pk=None):
        """Annule une notification en attente."""
        notif = self.get_object()
        if notif.status in (NotificationStatus.SENT, NotificationStatus.DELIVERED):
            return Response(
                {"detail": "Notification déjà envoyée — annulation impossible."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notif.status = NotificationStatus.CANCELLED
        notif.save(update_fields=["status", "updated_at"])
        log_action(
            notification=notif, action=Actions.CANCEL,
            actor=request.user, request=request,
        )
        return Response(NotificationSerializer(notif).data)


# ===========================================================================
# WEBHOOKS — delivery reports providers
# ===========================================================================

def _update_notification_status(provider_message_id: str, new_status: str, error: str = "") -> bool:
    """Met à jour le statut d'une notification depuis un webhook fournisseur."""
    notif = Notification.objects.filter(provider_message_id=provider_message_id).first()
    if not notif:
        logger.warning("Webhook %s : notification %s introuvable", new_status, provider_message_id)
        return False

    updates = ["status", "updated_at"]
    notif.status = new_status
    if new_status == NotificationStatus.DELIVERED:
        notif.delivered_at = timezone.now()
        updates.append("delivered_at")
    elif new_status == NotificationStatus.FAILED:
        notif.failed_at = timezone.now()
        notif.error_message = (error or "")[:1000]
        updates += ["failed_at", "error_message"]
    notif.save(update_fields=updates)

    log_action(
        notification=notif,
        action=Actions.DELIVERED if new_status == NotificationStatus.DELIVERED else Actions.FAILED,
        metadata={"webhook": True, "raw_status": new_status},
    )
    return True


class TwilioSmsStatusWebhookView(APIView):
    """POST /api/v1/notifications/webhooks/twilio/sms/status/ — delivery report Twilio."""
    permission_classes = [AllowAny]

    def post(self, request):
        cfg = getattr(settings, "NOTIFICATIONS", {})
        auth_token = cfg.get("TWILIO_AUTH_TOKEN", "")
        if auth_token and not self._verify_twilio_signature(request, auth_token):
            return Response({"detail": "Invalid signature"}, status=403)

        data = request.data
        sid = data.get("MessageSid") or data.get("SmsSid") or ""
        twilio_status = (data.get("MessageStatus") or data.get("SmsStatus") or "").lower()
        error_code = data.get("ErrorCode") or ""

        mapped = {
            "delivered": NotificationStatus.DELIVERED,
            "sent": NotificationStatus.SENT,
            "failed": NotificationStatus.FAILED,
            "undelivered": NotificationStatus.FAILED,
            "queued": NotificationStatus.QUEUED,
        }.get(twilio_status)

        if not mapped or not sid:
            return Response({"detail": "ignored"}, status=200)

        _update_notification_status(
            sid, mapped, error=f"Twilio code={error_code}" if error_code else "",
        )
        return Response({"ok": True})

    @staticmethod
    def _verify_twilio_signature(request, auth_token: str) -> bool:
        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            return False
        url = request.build_absolute_uri().split("?")[0]
        params = sorted(request.data.items()) if hasattr(request.data, "items") else []
        data_to_sign = url + "".join(f"{k}{v}" for k, v in params)
        mac = hmac.new(auth_token.encode(), data_to_sign.encode(), sha1)
        expected = b64encode(mac.digest()).decode()
        return hmac.compare_digest(expected, signature)


class OrangeCiSmsStatusWebhookView(APIView):
    """POST /api/v1/notifications/webhooks/orange-ci/sms/status/ — delivery report Orange CI."""
    permission_classes = [AllowAny]

    def post(self, request):
        cfg = getattr(settings, "NOTIFICATIONS", {})
        expected_token = cfg.get("ORANGE_CI_WEBHOOK_TOKEN", "")
        if expected_token:
            received = request.headers.get("X-Orange-Webhook-Token", "")
            if not hmac.compare_digest(expected_token, received):
                return Response({"detail": "Invalid token"}, status=403)

        data = request.data.get("deliveryInfoNotification", {}) or {}
        delivery_info = data.get("deliveryInfo", {}) or {}
        callback_data = data.get("callbackData", "")
        delivery_status = (delivery_info.get("deliveryStatus") or "").lower()

        mapped = {
            "delivered": NotificationStatus.DELIVERED,
            "deliveredtoterminal": NotificationStatus.DELIVERED,
            "deliveredtonetwork": NotificationStatus.SENT,
            "deliveryimpossible": NotificationStatus.FAILED,
            "deliveryuncertain": NotificationStatus.SENT,
        }.get(delivery_status)

        if not mapped:
            logger.info(
                "Orange CI webhook : status %r non mappé, callback=%s",
                delivery_status, callback_data,
            )
            return Response({"ok": True, "ignored": True})

        # callbackData = notif.id (envoyé dans le receiptRequest côté send_sms).
        # Lookup par PK puis fallback provider_message_id (compat) puis adresse.
        notif = None
        if callback_data and str(callback_data).isdigit():
            notif = Notification.objects.filter(pk=int(callback_data)).first()
        if notif is None and callback_data:
            notif = Notification.objects.filter(
                provider_message_id=callback_data
            ).first()
        if notif is None:
            addr = (delivery_info.get("address") or "").lstrip("tel:").strip()
            if addr:
                notif = (
                    Notification.objects
                    .filter(normalized_phone=addr, provider=Provider.ORANGE_CI)
                    .order_by("-created_at")
                    .first()
                )

        if notif is None:
            logger.warning(
                "Orange CI webhook : notif introuvable (callback=%s status=%s)",
                callback_data, delivery_status,
            )
            return Response({"ok": True, "not_found": True})

        if notif.provider_message_id:
            _update_notification_status(notif.provider_message_id, mapped)
        else:
            notif.status = mapped
            updates = ["status", "updated_at"]
            if mapped == NotificationStatus.DELIVERED:
                notif.delivered_at = timezone.now()
                updates.append("delivered_at")
            elif mapped == NotificationStatus.FAILED:
                notif.failed_at = timezone.now()
                updates.append("failed_at")
            notif.save(update_fields=updates)
        return Response({"ok": True})


# ===========================================================================
# WEBHOOKS WHATSAPP (Phase C)
# ===========================================================================

def _whatsapp_status_to_notif_status(wa_status: str) -> str:
    """Mapping canonical WhatsApp → NotificationStatus."""
    return {
        "sent": NotificationStatus.SENT,
        "delivered": NotificationStatus.DELIVERED,
        "read": NotificationStatus.DELIVERED,  # on traite read comme delivered
        "failed": NotificationStatus.FAILED,
        "queued": NotificationStatus.QUEUED,
    }.get(wa_status, NotificationStatus.SENT)


class TwilioWhatsAppStatusWebhookView(APIView):
    """POST /api/v1/notifications/webhooks/twilio/whatsapp/status/."""
    permission_classes = [AllowAny]

    def post(self, request):
        from .services.whatsapp_twilio import TwilioWhatsAppProvider
        provider = TwilioWhatsAppProvider()
        if not provider.validate_webhook(request):
            return Response({"detail": "Invalid signature"}, status=403)

        event = provider.parse_status_webhook(request.data)
        if not event or not event.provider_message_id:
            return Response({"detail": "ignored"}, status=200)

        _update_notification_status(
            event.provider_message_id,
            _whatsapp_status_to_notif_status(event.status),
            error=event.error,
        )
        return Response({"ok": True})


class MetaWhatsAppWebhookView(APIView):
    """Endpoint webhook Meta — GET (vérification) + POST (events).

    Meta envoie un GET `?hub.mode=subscribe&hub.verify_token=X&hub.challenge=Y`
    pour valider la subscription. On doit retourner le challenge en plain text
    si le verify_token correspond.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Vérification d'abonnement Meta
        cfg = getattr(settings, "NOTIFICATIONS", {})
        expected = cfg.get("META_WHATSAPP_VERIFY_TOKEN", "")
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge", "")
        if mode == "subscribe" and expected and token == expected:
            # Meta exige une réponse en texte brut (pas JSON)
            from django.http import HttpResponse
            return HttpResponse(challenge, content_type="text/plain")
        return Response({"detail": "Invalid token"}, status=403)

    def post(self, request):
        from .services.whatsapp_meta import MetaWhatsAppProvider
        provider = MetaWhatsAppProvider()
        if not provider.validate_webhook(request):
            return Response({"detail": "Invalid signature"}, status=403)

        event = provider.parse_status_webhook(request.data)
        if event and event.provider_message_id:
            _update_notification_status(
                event.provider_message_id,
                _whatsapp_status_to_notif_status(event.status),
                error=event.error,
            )
        # Meta exige toujours 200 OK rapide pour éviter les retries
        return Response({"ok": True})


# ---------------------------------------------------------------------------
# Historique notifications d'un voyageur
# ---------------------------------------------------------------------------
class TravelerNotificationsView(APIView):
    """GET /api/v1/notifications/traveler/<public_id>/ — historique."""
    permission_classes = [CanViewNotifications]

    def get(self, request, public_id):
        traveler = Traveler.objects.filter(public_id=public_id).first()
        if not traveler:
            return Response({"detail": "Voyageur introuvable."}, status=404)
        qs = traveler.notifications.select_related(
            "template", "sent_by"
        ).order_by("-created_at")[:200]
        return Response({
            "count": qs.count(),
            "results": NotificationSerializer(qs, many=True).data,
        })


# ===========================================================================
# EMAIL — ViewSet + webhook AWS SES
# ===========================================================================
import json  # noqa: E402

from .email_models import (  # noqa: E402
    EmailLog, EmailStatus, EmailTemplate, SenderProfile,
)
from .serializers import (  # noqa: E402
    EmailLogSerializer, EmailTemplateSerializer, SenderProfileSerializer,
)


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/notifications/emails/ — historique des emails envoyés."""
    queryset = (
        EmailLog.objects
        .select_related("template", "related_user", "related_traveler", "sent_by")
        .order_by("-created_at")
    )
    serializer_class = EmailLogSerializer
    permission_classes = [CanViewNotifications]
    filterset_fields = ["status", "email_type", "sender_address", "related_user", "related_traveler"]
    search_fields = ["recipient", "subject", "error_message"]

    @action(detail=True, methods=["post"], permission_classes=[CanRetryNotification])
    def retry(self, request, pk=None):
        """Relance manuellement un email FAILED."""
        log = self.get_object()
        if log.status not in (EmailStatus.FAILED, EmailStatus.CANCELLED, EmailStatus.BOUNCED):
            return Response(
                {"detail": "Seuls les emails FAILED / CANCELLED / BOUNCED peuvent être relancés."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        log.status = EmailStatus.QUEUED
        log.error_message = ""
        log.save(update_fields=["status", "error_message", "updated_at"])

        from .tasks_email import send_email_task
        send_email_task.delay(log.id)
        return Response(EmailLogSerializer(log).data)

    @action(
        detail=False, methods=["post"], url_path="bulk-retry",
        permission_classes=[CanRetryNotification],
    )
    def bulk_retry(self, request):
        """Relance en lot. Body: {"ids":[1,2]} OU {"all_failed": true, "max_age_hours": 24}."""
        ids = request.data.get("ids") or []
        all_failed = bool(request.data.get("all_failed"))
        max_age_hours = int(request.data.get("max_age_hours") or 24)

        if not ids and not all_failed:
            return Response(
                {"detail": "Fournir 'ids' (liste) ou 'all_failed': true."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = EmailLog.objects.filter(status__in=(
            EmailStatus.FAILED, EmailStatus.CANCELLED, EmailStatus.BOUNCED,
        ))
        if ids:
            try:
                ids_int = [int(i) for i in ids][:500]
            except (ValueError, TypeError):
                return Response({"detail": "IDs invalides."}, status=400)
            qs = qs.filter(pk__in=ids_int)
        elif all_failed:
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(hours=max_age_hours)
            qs = qs.filter(failed_at__gte=cutoff)[:500]

        from .tasks_email import send_email_task
        requeued = 0
        results = []
        for log in qs:
            log.status = EmailStatus.QUEUED
            log.error_message = ""
            log.save(update_fields=["status", "error_message", "updated_at"])
            send_email_task.delay(log.id)
            requeued += 1
            results.append({"id": log.id, "recipient": log.masked_recipient})
        return Response({"ok": True, "requeued": requeued, "results": results})


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """CRUD des templates email — réservé aux admins (HasRole côté router)."""
    queryset = EmailTemplate.objects.all().order_by("email_type", "code")
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["email_type", "is_active", "sender_profile"]
    search_fields = ["code", "name", "subject"]


class SenderProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """Lecture seule des profils — l'édition se fait via Django admin uniquement."""
    queryset = SenderProfile.objects.all().order_by("code")
    serializer_class = SenderProfileSerializer
    permission_classes = [IsAuthenticated]


# ---------------------------------------------------------------------------
# Webhook AWS SES — événements SNS (delivered / bounced / complained)
# ---------------------------------------------------------------------------
class AwsSesEventWebhookView(APIView):
    """POST /api/v1/notifications/webhooks/ses/events/

    SES envoie ses événements via SNS. Format attendu :
        {
          "Type": "Notification",
          "Message": "{...JSON SES event...}"
        }
    Le `Message` contient `eventType` (Delivery / Bounce / Complaint / Open)
    et `mail.messageId` qu'on retrouve dans `EmailLog.provider_message_id`.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    SES_TO_STATUS = {
        "Delivery": EmailStatus.DELIVERED,
        "Bounce": EmailStatus.BOUNCED,
        "Complaint": EmailStatus.BOUNCED,  # plainte → traité comme bounce
        "Open": EmailStatus.OPENED,
        "Click": EmailStatus.CLICKED,
    }

    def post(self, request):
        payload = request.data
        msg_type = payload.get("Type")

        # SNS subscription confirmation : on log + accepte
        if msg_type == "SubscriptionConfirmation":
            logger.info("SES SNS SubscriptionConfirmation reçue — URL: %s",
                        payload.get("SubscribeURL", "")[:200])
            return Response({"ok": True, "subscription": "pending"})

        if msg_type != "Notification":
            return Response({"ok": True, "ignored": "type=" + str(msg_type)})

        # Le message SNS est une string JSON imbriquée
        raw = payload.get("Message", "")
        try:
            event = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return Response({"detail": "Invalid Message JSON"}, status=400)

        event_type = event.get("eventType") or event.get("notificationType")
        mapped_status = self.SES_TO_STATUS.get(event_type)
        if not mapped_status:
            return Response({"ok": True, "ignored": event_type})

        # Lookup par provider_message_id (SES messageId)
        message_id = (event.get("mail") or {}).get("messageId", "")
        if not message_id:
            return Response({"ok": True, "skipped": "no messageId"})

        log = EmailLog.objects.filter(provider_message_id=message_id).first()
        if not log:
            logger.info("SES webhook : EmailLog introuvable pour messageId=%s", message_id)
            return Response({"ok": True, "not_found": True})

        # Extraire erreur si bounce/complaint
        error = ""
        if event_type == "Bounce":
            recips = event.get("bounce", {}).get("bouncedRecipients", [])
            if recips:
                error = recips[0].get("diagnosticCode", "")
        elif event_type == "Complaint":
            error = "Plainte spam destinataire"

        log.status = mapped_status
        if mapped_status == EmailStatus.DELIVERED:
            log.delivered_at = timezone.now()
        elif mapped_status == EmailStatus.BOUNCED:
            log.failed_at = timezone.now()
            log.error_message = error[:1000]
        log.save()
        logger.info("SES event %s → EmailLog #%s (%s)", event_type, log.id, mapped_status)
        return Response({"ok": True, "log_id": log.id, "status": mapped_status})


class EmailSmtpTestView(APIView):
    """POST /api/v1/notifications/email-test/

    Body : {"profile": "public"|"internal", "recipient": "email@x.com"}
    Envoie un email de test direct via la connexion SMTP du profil pour
    valider la config sans passer par les templates.
    Réservé authenticated (front filtre côté nav pour Super Admin).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .services.email_router import _build_connection
        from django.core.mail import EmailMultiAlternatives

        profile_code = (request.data.get("profile") or "").lower()
        recipient = (request.data.get("recipient") or "").strip()

        if profile_code not in ("public", "internal"):
            return Response(
                {"detail": "profile doit être 'public' ou 'internal'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not recipient or "@" not in recipient:
            return Response({"detail": "Email destinataire invalide."}, status=400)

        profiles = getattr(settings, "EMAIL_PROFILES", {})
        cfg = profiles.get(profile_code) or {}
        from_addr = cfg.get("from_address", "")
        from_name = cfg.get("from_name", "")

        try:
            connection = _build_connection(profile_code)
            from_header = f"{from_name} <{from_addr}>" if from_name else from_addr
            msg = EmailMultiAlternatives(
                subject=f"[Test EpiTrace] Profil {profile_code.upper()}",
                body=(
                    f"Bonjour,\n\nCeci est un email de test envoyé via le profil "
                    f"{profile_code.upper()} d'EpiTrace ({from_addr}).\n\n"
                    f"Hôte SMTP : {cfg.get('host')}:{cfg.get('port')}\n\n"
                    f"Si vous recevez ce message, la configuration SMTP est OK.\n\n"
                    "— EpiTrace / INHP"
                ),
                from_email=from_header,
                to=[recipient],
                connection=connection,
            )
            sent = msg.send(fail_silently=False)
            return Response({
                "ok": True,
                "sent": sent,
                "profile": profile_code,
                "host": cfg.get("host"),
                "port": cfg.get("port"),
                "from": from_header,
            })
        except Exception as exc:  # noqa: BLE001
            return Response({
                "ok": False,
                "error": str(exc),
                "profile": profile_code,
                "host": cfg.get("host"),
                "port": cfg.get("port"),
            }, status=200)  # 200 pour pouvoir lire l'erreur côté front
