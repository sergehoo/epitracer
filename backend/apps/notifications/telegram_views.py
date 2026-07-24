"""Endpoints Telegram — webhook + statut de liaison pour l'espace voyageur.

Routes exposées :
  - POST /api/v1/telegram/webhook/     (public, signature validée)
  - GET  /api/v1/me/telegram/          (public voyageur, session-cookie)
  - POST /api/v1/telegram/unlink/      (voyageur ou admin)
  - GET  /api/v1/telegram/config/      (admin — deep link + statut bot)
"""
from __future__ import annotations

import logging

from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import TelegramSubscription
from .services.telegram import (
    build_deep_link,
    get_bot_username,
    handle_incoming_update,
    is_configured,
    verify_webhook_secret,
)

logger = logging.getLogger("epidemitracker.notifications.telegram_views")


# ---------------------------------------------------------------------------
# Webhook — appelé par Telegram après chaque message envoyé au bot
# ---------------------------------------------------------------------------
class TelegramWebhookThrottle(AnonRateThrottle):
    scope = "telegram_webhook"
    rate = "120/minute"  # Telegram peut envoyer en rafale sur groupes


class TelegramWebhookView(APIView):
    """POST reçu par Telegram après chaque update destiné au bot.

    Sécurité :
      1. Header `X-Telegram-Bot-Api-Secret-Token` matché au TELEGRAM_WEBHOOK_SECRET
      2. Payload borné aux commandes whitelistées (start/stop/help/link)
      3. Throttle 120/min pour absorber un pic sans risque
    """
    permission_classes = [AllowAny]
    throttle_classes = [TelegramWebhookThrottle]

    def post(self, request):
        # 1. Validation signature
        provided_secret = request.META.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "")
        if not verify_webhook_secret(provided_secret):
            logger.warning("Telegram webhook rejected — invalid secret from %s",
                           request.META.get("REMOTE_ADDR", "?"))
            return Response({"detail": "Unauthorized"}, status=401)

        # 2. Handling
        try:
            result = handle_incoming_update(request.data or {})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Telegram webhook handling failed : %s", exc)
            # On répond 200 quand même pour éviter que Telegram ne re-tente en boucle
            return Response({"ok": False, "error": "internal"}, status=200)

        return Response({"ok": True, **result})


# ---------------------------------------------------------------------------
# Statut voyageur — pour l'espace /voyageur/suivi (bouton Telegram)
# ---------------------------------------------------------------------------
class MyTelegramStatusView(APIView):
    """GET /api/v1/me/telegram/?traveler=TRV-XXX

    Le paramètre `traveler` doit correspondre au public_id — pas d'auth stricte
    car cette page voyageur utilise déjà un signed link ou une session cookie
    minimale. Le view retourne juste l'état de liaison + le lien deep-link
    à cliquer.

    ⚠️ Aucune PII n'est renvoyée : uniquement { linked, deep_link, bot_username }.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from apps.travelers.models import Traveler

        public_id = (request.query_params.get("traveler") or "").strip().upper()
        if not public_id:
            return Response({"detail": "Paramètre 'traveler' requis."}, status=400)

        traveler = Traveler.objects.filter(public_id=public_id).first()
        if not traveler:
            return Response({"detail": "Voyageur introuvable."}, status=404)

        subs = TelegramSubscription.objects.filter(
            traveler=traveler, is_active=True,
        )
        return Response({
            "linked": subs.exists(),
            "chats_count": subs.count(),
            "bot_username": get_bot_username(),
            "deep_link": build_deep_link(traveler.public_id),
            "configured": is_configured(),
        })


# ---------------------------------------------------------------------------
# Désinscription — voyageur ou admin
# ---------------------------------------------------------------------------
class TelegramUnlinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        traveler_id = request.data.get("traveler")
        chat_id = (request.data.get("chat_id") or "").strip()

        qs = TelegramSubscription.objects.filter(is_active=True)
        if chat_id:
            qs = qs.filter(chat_id=chat_id)
        elif traveler_id:
            qs = qs.filter(traveler_id=traveler_id)
        else:
            return Response({"detail": "traveler ou chat_id requis."}, status=400)

        updated = qs.update(is_active=False)
        return Response({"ok": True, "deactivated": updated})


# ---------------------------------------------------------------------------
# Config publique (admin) — pour la page paramètres notifications
# ---------------------------------------------------------------------------
class TelegramConfigView(APIView):
    """GET admin — vérifie que le bot est bien configuré + retourne son @."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings as _s

        return Response({
            "configured": is_configured(),
            "bot_username": get_bot_username(),
            "webhook_secret_set": bool(getattr(_s, "TELEGRAM_WEBHOOK_SECRET", "")),
            "webhook_url_expected": (
                f"{_s.SITE_URL_API}/api/v1/telegram/webhook/"
                if getattr(_s, "SITE_URL_API", None) else ""
            ),
        })


class TelegramLinkStatusView(APIView):
    """POST admin — pour une liste de traveler_ids, retourne combien sont
    liés Telegram (au moins 1 chat actif) vs non-liés.

    Utilisé par la modale d'envoi groupé pour afficher :
      "27 sur 100 voyageurs ont Telegram activé — 73 recevront un SMS d'invitation"

    Body : { "traveler_ids": [1, 2, 3, ...] }
    Response : {
        "total": 100,
        "linked": 27,
        "unlinked": 73,
        "linked_ids": [2, 5, 8, ...],   // Pour segmentation front
        "bot_configured": true,
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_ids = request.data.get("traveler_ids") or []
        if not isinstance(raw_ids, list):
            return Response({"detail": "'traveler_ids' doit être une liste."}, status=400)

        ids = []
        for v in raw_ids:
            try:
                ids.append(int(v))
            except (TypeError, ValueError):
                continue

        if not ids:
            return Response({
                "total": 0, "linked": 0, "unlinked": 0,
                "linked_ids": [],
                "bot_configured": is_configured(),
            })

        # Borne défensive : max 5000 ids par requête (~500 KB, très large)
        ids = ids[:5000]

        linked_ids = list(
            TelegramSubscription.objects
            .filter(traveler_id__in=ids, is_active=True)
            .values_list("traveler_id", flat=True)
            .distinct()
        )
        linked_set = set(linked_ids)

        return Response({
            "total": len(ids),
            "linked": len(linked_set),
            "unlinked": len(ids) - len(linked_set),
            "linked_ids": sorted(linked_set),
            "bot_configured": is_configured(),
        })
