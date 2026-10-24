"""Authentification voyageur — passport + téléphone + OTP SMS.

Ce flow est distinct de celui des agents INHP (qui passe par
EpidemiTokenObtainPairView + MFA email). Un voyageur n'a pas de mot de passe :
il reçoit un OTP par SMS sur le numéro qu'il a renseigné lors de son
inscription publique.

Endpoints :
    POST /api/mobile/auth/voyageur/request-otp/
        body : { passport_number, phone }  (au moins l'un des deux)
    POST /api/mobile/auth/voyageur/verify-otp/
        body : { passport_number, phone, code }
        return: { access, refresh, traveler: {...} }
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core import ratelimit, turnstile
from apps.core.ratelimit import client_ip
from apps.notifications.models import MessageType
from apps.notifications.services.dispatcher import enqueue_notification
from apps.notifications.services.router import PhoneValidationError, normalize_phone_number
from apps.notifications.services.security import SecurityEventKind, log_security_event
from apps.travelers.models import Traveler

logger = logging.getLogger(__name__)
User = get_user_model()

OTP_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5


def _mask_phone(phone: str) -> str:
    """+22507****0000"""
    if not phone or len(phone) < 8:
        return phone or ""
    return phone[:5] + "****" + phone[-4:]


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    """6 chiffres aléatoires."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _find_traveler(passport_number: str | None, phone: str | None) -> Traveler | None:
    """Voyageur par n° de pièce d'identité, sinon par téléphone (E.164)."""
    qs = Traveler.objects.all()
    if passport_number:
        match = qs.filter(id_document_number__iexact=passport_number.strip()).first()
        if match:
            return match
    if phone:
        try:
            normalized = normalize_phone_number(phone)
        except PhoneValidationError:
            return None
        raw = phone.replace(" ", "").replace("-", "")
        return qs.filter(phone_mobile__in={normalized, raw}).first()
    return None


def _traveler_phone(traveler: Traveler | None) -> str:
    """Numéro E.164 enregistré du voyageur (seul destinataire possible)."""
    if traveler is None or not traveler.phone_mobile:
        return ""
    try:
        return normalize_phone_number(traveler.phone_mobile)
    except PhoneValidationError:
        return ""


NEUTRAL_MESSAGE = "Si vous êtes enregistré, un code SMS vient d'être envoyé."


def _neutral(supplied_phone: str = "") -> Response:
    """Réponse identique dans tous les cas (anti-énumération, anti-sondage) :
    seul le numéro fourni par le client est renvoyé, masqué."""
    try:
        shown = normalize_phone_number(supplied_phone) if supplied_phone else ""
    except PhoneValidationError:
        shown = supplied_phone
    return Response(
        {"ok": True, "phone_masked": _mask_phone(shown), "message": NEUTRAL_MESSAGE},
        status=status.HTTP_200_OK,
    )


def _too_many(result) -> Response:
    resp = Response(
        {"detail": "Trop de demandes de code. Réessayez plus tard."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    resp["Retry-After"] = str(result.retry_after)
    return resp


class VoyageurRequestOtpView(APIView):
    """Génère un code OTP et l'envoie par SMS au numéro ENREGISTRÉ du voyageur.

    Protections anti SMS pumping (le SMS n'est jamais envoyé à un numéro
    fourni dans la requête, uniquement à celui de la fiche voyageur) :
      - ScopedRateThrottle ``mobile_otp_request`` (3/min/IP) ;
      - Turnstile vérifié côté serveur (action ``otp_request``) si activé ;
      - fenêtres Redis atomiques par IP, par numéro et par endpoint ;
      - un seul code par voyageur et par minute (rejeu de requête) ;
      - quotas OTP par numéro, budget et coupe-circuit dans le dispatcher.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_otp_request"

    def post(self, request):
        passport = request.data.get("passport_number") or ""
        phone = request.data.get("phone") or ""

        if not passport and not phone:
            return Response(
                {"detail": "passport_number ou phone requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        captcha = turnstile.check_request(request, "otp_request")
        if not captcha.ok:
            return Response(
                {"detail": turnstile.failure_message(captcha)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ip = client_ip(request)
        for rule, identity in (("otp_request_ip", ip), ("otp_request_endpoint", "all")):
            result = ratelimit.hit(rule, identity)
            if not result.allowed:
                log_security_event(
                    SecurityEventKind.RATE_LIMITED, source="otp_request", ip=ip,
                    details={"rule": rule, "count": result.count, "limit": result.limit},
                    dedupe=f"otp:{rule}:{identity}",
                )
                return _too_many(result)

        traveler = _find_traveler(passport, phone)
        to = _traveler_phone(traveler)
        if not to:
            return _neutral(phone)

        # Par numéro (l'attaquant peut tourner d'IP) puis délai entre 2 codes.
        result = ratelimit.hit("otp_request_phone", to)
        if not result.allowed:
            log_security_event(
                SecurityEventKind.RATE_LIMITED, source="otp_request", ip=ip, phone=to,
                traveler=traveler, details={"rule": "otp_request_phone", "limit": result.limit},
                dedupe=f"otp:phone:{to}",
            )
            return _neutral(phone)
        _limit, cooldown = settings.PUBLIC_RATE_LIMITS["otp_cooldown"]
        if not cache.add(f"voyageur_otp_cooldown:{traveler.pk}", 1, timeout=cooldown):
            return _neutral(phone)

        code = _generate_otp()
        cache.set(
            f"voyageur_otp:{traveler.pk}",
            {"hash": _hash_otp(code), "attempts": 0, "phone": to},
            timeout=int(OTP_TTL.total_seconds()),
        )

        # Envoi via le dispatcher : routage Orange CI / Twilio strict, quotas
        # OTP par numéro, budget et coupe-circuit, historique.
        res = enqueue_notification(
            channel="sms",
            recipient=to,
            traveler=traveler,
            body=(
                "Mon Pass Sanitaire INHP\n"
                f"Votre code de connexion : {code}\n"
                "Valable 10 minutes. Ne le partagez avec personne."
            ),
            message_type=MessageType.OTP,
            metadata={"kind": "otp", "ip": ip},
        )
        if not res.ok:
            logger.warning(
                "Voyageur OTP non envoyé traveler=%s phone=%s code=%s",
                traveler.pk, _mask_phone(to), res.error_code or res.error,
            )
            return _neutral(phone)

        logger.info("Voyageur OTP issued for traveler=%s phone=%s", traveler.pk, _mask_phone(to))
        return _neutral(phone)


class VoyageurVerifyOtpView(APIView):
    """Vérifie l'OTP et renvoie un couple JWT (access+refresh) pour le voyageur.

    Le couple JWT est lié à un User "shadow" créé automatiquement pour le
    Traveler (username = traveler:<id>) pour profiter de l'infrastructure
    SimpleJWT existante, mais sans droits admin.

    task #213 : rate-limité comme un login (``mobile_login`` = 10/min/IP).
    Un code déjà utilisé est refusé (rejeu journalisé).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_login"

    def post(self, request):
        passport = request.data.get("passport_number") or ""
        phone = request.data.get("phone") or ""
        code = (request.data.get("code") or "").strip()

        if not code or len(code) != 6:
            return Response(
                {"detail": "Code à 6 chiffres requis"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        traveler = _find_traveler(passport, phone)
        if not traveler:
            return Response(
                {"detail": "Identification voyageur impossible"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cache_key = f"voyageur_otp:{traveler.pk}"
        used_key = f"voyageur_otp_used:{traveler.pk}:{_hash_otp(code)}"
        data = cache.get(cache_key)
        if not data:
            if cache.get(used_key):
                log_security_event(
                    SecurityEventKind.OTP_REPLAY, source="otp_verify", ip=client_ip(request),
                    phone=_traveler_phone(traveler), traveler=traveler,
                    dedupe=f"otp_replay:{traveler.pk}",
                )
            return Response(
                {"detail": "Code expiré ou inexistant. Demandez un nouveau code."},
                status=status.HTTP_410_GONE,
            )

        attempts = int(data.get("attempts", 0))
        if attempts >= MAX_ATTEMPTS:
            cache.delete(cache_key)
            return Response(
                {"detail": "Trop de tentatives. Demandez un nouveau code."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if _hash_otp(code) != data["hash"]:
            data["attempts"] = attempts + 1
            cache.set(cache_key, data, timeout=int(OTP_TTL.total_seconds()))
            return Response(
                {"detail": "Code incorrect"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # OTP valide → consommé une seule fois (le rejeu sera détecté).
        cache.delete(cache_key)
        cache.set(used_key, 1, timeout=int(OTP_TTL.total_seconds()))

        # Crée (ou récupère) le User shadow lié au Traveler
        shadow_user = self._ensure_shadow_user(traveler)

        refresh = RefreshToken.for_user(shadow_user)
        refresh["scope"] = "voyageur"
        refresh["traveler_id"] = traveler.pk

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "traveler": {
                    "id": traveler.pk,
                    "public_id": traveler.public_id,
                    "full_name": f"{traveler.first_name} {traveler.last_name}".strip(),
                    "phone_masked": _mask_phone(_traveler_phone(traveler)),
                    "passport_number": traveler.id_document_number,
                },
            }
        )

    @staticmethod
    @transaction.atomic
    def _ensure_shadow_user(traveler: Traveler) -> User:
        username = f"voyageur_{traveler.pk}"
        email = traveler.email or f"voyageur_{traveler.pk}@no-reply.veillesanitaire.com"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": traveler.first_name or "",
                "last_name": traveler.last_name or "",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if created:
            user.set_unusable_password()
            user.save()
        return user
