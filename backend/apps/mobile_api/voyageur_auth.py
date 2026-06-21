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

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

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
    qs = Traveler.objects.all()
    if passport_number:
        match = qs.filter(passport_number__iexact=passport_number.strip()).first()
        if match:
            return match
    if phone:
        normalized = phone.replace(" ", "").replace("-", "")
        # Possible variantes : avec ou sans indicatif
        return qs.filter(phone_e164__iexact=normalized).first()
    return None


class VoyageurRequestOtpView(APIView):
    """Génère un code OTP, l'envoie par SMS au voyageur identifié.

    task #213 : protégé par ScopedRateThrottle ``mobile_otp_request`` (3/min/IP)
    + cooldown applicatif par phone (max 5/heure) — empêche le spam SMS même
    si l'attaquant change d'IP.
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

        traveler = _find_traveler(passport, phone)
        if not traveler or not traveler.phone_e164:
            # Réponse neutre pour éviter l'énumération
            return Response(
                {
                    "ok": True,
                    "phone_masked": _mask_phone(phone or ""),
                    "message": "Si vous êtes enregistré, un code SMS vient d'être envoyé.",
                },
                status=status.HTTP_200_OK,
            )

        # task #213 — cooldown applicatif par phone : max 5/heure même si
        # l'attaquant tourne d'IP. Stocké en cache Redis (sliding window).
        from django.core.cache import cache

        phone_quota_key = f"voyageur_otp_quota:{traveler.phone_e164}"
        phone_count = cache.get(phone_quota_key, 0)
        if phone_count >= 5:
            logger.warning(
                "Voyageur OTP quota hit for phone=%s ip=%s",
                _mask_phone(traveler.phone_e164),
                request.META.get("REMOTE_ADDR", "?"),
            )
            return Response(
                {
                    "ok": True,  # neutralité anti-énumération
                    "phone_masked": _mask_phone(traveler.phone_e164),
                    "message": "Si vous êtes enregistré, un code SMS vient d'être envoyé.",
                },
                status=status.HTTP_200_OK,
            )
        cache.set(phone_quota_key, phone_count + 1, timeout=3600)

        code = _generate_otp()
        otp_hash = _hash_otp(code)
        cache_key = f"voyageur_otp:{traveler.pk}"

        # Stocker le hash + nb tentatives en cache (Redis)
        cache.set(
            cache_key,
            {"hash": otp_hash, "attempts": 0, "phone": traveler.phone_e164},
            timeout=int(OTP_TTL.total_seconds()),
        )

        # Envoyer via le router SMS existant (Orange CI / Twilio)
        try:
            from apps.notifications.services import send_sms

            send_sms(
                to=traveler.phone_e164,
                body=(
                    f"Mon Pass Sanitaire INHP\n"
                    f"Votre code de connexion : {code}\n"
                    f"Valable 10 minutes. Ne le partagez avec personne."
                ),
                category="otp",
            )
        except Exception as exc:  # noqa
            logger.warning("Voyageur OTP SMS send failed: %s", exc)

        logger.info(
            "Voyageur OTP issued for traveler=%s phone=%s",
            traveler.pk,
            _mask_phone(traveler.phone_e164),
        )

        return Response(
            {
                "ok": True,
                "phone_masked": _mask_phone(traveler.phone_e164),
                "message": "Code envoyé par SMS",
            }
        )


class VoyageurVerifyOtpView(APIView):
    """Vérifie l'OTP et renvoie un couple JWT (access+refresh) pour le voyageur.

    Le couple JWT est lié à un User "shadow" créé automatiquement pour le
    Traveler (username = traveler:<id>) pour profiter de l'infrastructure
    SimpleJWT existante, mais sans droits admin.

    task #213 : rate-limité comme un login (``mobile_login`` = 10/min/IP).
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

        from django.core.cache import cache

        cache_key = f"voyageur_otp:{traveler.pk}"
        data = cache.get(cache_key)
        if not data:
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

        # OTP valide → on consomme
        cache.delete(cache_key)

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
                    "phone_masked": _mask_phone(traveler.phone_e164),
                    "passport_number": traveler.passport_number,
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
