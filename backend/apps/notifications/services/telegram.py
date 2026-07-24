"""Service d'envoi et de gestion des messages Telegram Bot API.

Le canal Telegram s'appuie sur un **bot** créé via @BotFather. Le bot expose
un token HTTP long à conserver secret (variable `TELEGRAM_BOT_TOKEN` du .env).

Flux d'inscription voyageur → bot :
    1. Le voyageur clique sur `t.me/<BOT>?start=<TRV-XXX>` (deep link généré
       dans /voyageur/suivi ou le carnet santé mobile).
    2. Telegram envoie POST au webhook `/api/v1/telegram/webhook/` avec le
       message initial `/start TRV-XXX` + les infos de son chat.
    3. `handle_incoming_update()` matche `TRV-XXX` sur Traveler.public_id
       et crée un `TelegramSubscription(traveler, chat_id, ...)`.
    4. Un accusé de bienvenue est envoyé au chat pour confirmer.

Sécurité :
    - Le webhook est protégé par un `secret_token` de 32+ caractères
      (feature native Telegram : header `X-Telegram-Bot-Api-Secret-Token`).
    - Le token du bot n'est jamais loggé en clair (`_mask_token`).
    - Les commandes acceptées sont whitelistées : /start /stop /help /link.
    - Pas de PII dans les logs — juste `chat_id` + type de commande.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests
from django.conf import settings

logger = logging.getLogger("epidemitracker.notifications.telegram")

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_TIMEOUT = 10
MAX_MESSAGE_LENGTH = 4096  # limite officielle Telegram


class TelegramNotConfigured(RuntimeError):
    """Levée si TELEGRAM_BOT_TOKEN n'est pas défini."""


@dataclass
class TelegramSendResult:
    ok: bool
    message_id: Optional[int] = None
    error: str = ""


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------
def _bot_token() -> str:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    if not token:
        raise TelegramNotConfigured(
            "TELEGRAM_BOT_TOKEN n'est pas configuré dans les settings."
        )
    return token


def _bot_url(method: str) -> str:
    return f"{TELEGRAM_API_BASE}/bot{_bot_token()}/{method}"


def _mask_token(token: str) -> str:
    """Masque le token pour les logs — 12 premiers caractères + '…'."""
    if not token or len(token) < 20:
        return "***"
    return f"{token[:8]}…{token[-4:]}"


def is_configured() -> bool:
    """True si le token bot est présent — utilisable en check-list admin."""
    return bool(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))


def get_bot_username() -> str:
    """Nom du bot (sans @) — utilisé pour construire les deep links."""
    return (getattr(settings, "TELEGRAM_BOT_USERNAME", "") or "").lstrip("@")


def build_deep_link(traveler_public_id: str) -> str:
    """Construit `https://t.me/<BOT>?start=<TRV-XXX>` pour l'inscription."""
    username = get_bot_username()
    if not username:
        return ""
    # Telegram remplace les tirets par des underscores dans le paramètre start
    payload = (traveler_public_id or "").strip().replace("-", "_")
    return f"https://t.me/{username}?start={payload}"


# ---------------------------------------------------------------------------
# Envoi de message
# ---------------------------------------------------------------------------
def send_message(
    chat_id: str,
    text: str,
    *,
    parse_mode: Optional[str] = "HTML",
    disable_web_page_preview: bool = True,
    reply_markup: Optional[dict] = None,
) -> TelegramSendResult:
    """Envoie un message texte à un chat Telegram (POST sendMessage).

    Args:
        chat_id: identifiant numérique du chat, en str.
        text: contenu (max 4096 caractères — tronqué si plus long).
        parse_mode: "HTML" (par défaut) ou "MarkdownV2" ou None.
        disable_web_page_preview: True pour ne pas générer d'aperçu URL.
        reply_markup: keyboard optionnel (dict conforme Bot API).

    Returns:
        TelegramSendResult avec `message_id` en cas de succès ou `error` sinon.
    """
    if not chat_id:
        return TelegramSendResult(ok=False, error="chat_id manquant.")
    if not text or not text.strip():
        return TelegramSendResult(ok=False, error="Message vide.")

    # Troncature défensive
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 3] + "..."

    try:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        r = requests.post(_bot_url("sendMessage"), json=payload, timeout=DEFAULT_TIMEOUT)
    except TelegramNotConfigured as exc:
        return TelegramSendResult(ok=False, error=str(exc))
    except requests.RequestException as exc:
        logger.warning("Telegram network error chat=%s : %s", chat_id, exc)
        return TelegramSendResult(ok=False, error=f"Erreur réseau : {exc}")

    if r.status_code != 200:
        # Les codes 403/400 typiques : bot bloqué, chat introuvable, etc.
        try:
            body = r.json()
        except Exception:  # noqa: BLE001
            body = {"raw": r.text[:200]}
        desc = body.get("description") if isinstance(body, dict) else str(body)
        logger.info(
            "Telegram sendMessage rejected chat=%s status=%s desc=%s",
            chat_id, r.status_code, desc,
        )
        return TelegramSendResult(ok=False, error=f"Telegram {r.status_code} : {desc}")

    data = r.json() or {}
    result = data.get("result") or {}
    return TelegramSendResult(ok=True, message_id=result.get("message_id"))


# ---------------------------------------------------------------------------
# Webhook — configuration + validation
# ---------------------------------------------------------------------------
def set_webhook(webhook_url: str, *, secret_token: str = "") -> dict:
    """POST setWebhook — à appeler une fois pour brancher le bot sur EpiTrace.

    Args:
        webhook_url: URL publique HTTPS (ex. https://api.veillesanitaire.com/api/v1/telegram/webhook/).
        secret_token: si fourni, Telegram enverra `X-Telegram-Bot-Api-Secret-Token`
            à chaque update — à valider dans le webhook.
    """
    payload = {"url": webhook_url, "allowed_updates": ["message", "callback_query"]}
    if secret_token:
        payload["secret_token"] = secret_token
    r = requests.post(_bot_url("setWebhook"), json=payload, timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_webhook_info() -> dict:
    r = requests.get(_bot_url("getWebhookInfo"), timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    return r.json()


def delete_webhook() -> dict:
    r = requests.post(_bot_url("deleteWebhook"), timeout=DEFAULT_TIMEOUT)
    r.raise_for_status()
    return r.json()


def verify_webhook_secret(request_secret: str) -> bool:
    """True si le header `X-Telegram-Bot-Api-Secret-Token` matche celui du settings.

    Utilisé par la view webhook pour rejeter les POST non signés.
    Retourne True aussi si aucun secret n'est configuré (mode dev/local).
    """
    expected = (getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or "").strip()
    if not expected:
        # Pas de secret configuré → on accepte (dev only).
        # ATTENTION : à activer obligatoirement en prod.
        logger.warning("Telegram webhook sans secret — mode dev uniquement.")
        return True
    return (request_secret or "").strip() == expected


# ---------------------------------------------------------------------------
# Handling des updates entrants
# ---------------------------------------------------------------------------
def handle_incoming_update(update: dict) -> dict:
    """Traite un update Telegram (payload webhook) et retourne un résumé JSON.

    Commandes supportées :
      /start <TRV-XXX>  → lie le chat au voyageur (crée TelegramSubscription)
      /stop             → désactive l'abonnement
      /help             → renvoie l'aide
      /link <TRV-XXX>   → alias de /start pour re-lier

    Toute autre message est stocké mais ignoré (pour l'instant on ne fait pas
    d'auto-répondeur — c'est un canal broadcast admin → voyageur).
    """
    from django.utils import timezone
    from apps.notifications.models import TelegramSubscription
    from apps.travelers.models import Traveler

    message = update.get("message") or update.get("edited_message") or {}
    if not message:
        return {"handled": False, "reason": "no_message"}

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = str(chat.get("id") or "")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"handled": False, "reason": "no_chat_id"}

    # Extraction commande + arg (accepte "/start TRV_XXX" ET "/start@Bot TRV_XXX")
    command = ""
    arg = ""
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd_full = parts[0]
        command = cmd_full.split("@")[0][1:].lower()  # /start@Bot → "start"
        arg = parts[1].strip() if len(parts) > 1 else ""

    # Normalisation : Telegram remplace les tirets par des underscores dans start
    def _normalize_public_id(raw: str) -> str:
        raw = (raw or "").strip().upper().replace("_", "-")
        return raw

    result = {"handled": True, "command": command, "chat_id": chat_id}

    if command in ("start", "link"):
        public_id = _normalize_public_id(arg)
        if not public_id:
            send_message(
                chat_id,
                "Bienvenue sur <b>Mon Pass Sanitaire — INHP</b>.\n\n"
                "Pour recevoir vos notifications, cliquez sur le lien fourni "
                "dans votre espace voyageur, ou tapez :\n"
                "<code>/link TRV-XXXXXXXX</code>",
            )
            result["status"] = "welcome_no_id"
            return result

        traveler = Traveler.objects.filter(public_id=public_id).first()
        if not traveler:
            send_message(
                chat_id,
                f"Voyageur <b>{public_id}</b> introuvable. Vérifiez votre "
                "identifiant dans votre espace personnel.",
            )
            result["status"] = "traveler_not_found"
            result["public_id"] = public_id
            return result

        sub, created = TelegramSubscription.objects.update_or_create(
            chat_id=chat_id,
            defaults={
                "traveler": traveler,
                "username": (from_user.get("username") or "")[:64],
                "first_name": (from_user.get("first_name") or "")[:120],
                "last_name": (from_user.get("last_name") or "")[:120],
                "language_code": (from_user.get("language_code") or "")[:8],
                "is_active": True,
                "last_message_at": timezone.now(),
            },
        )
        send_message(
            chat_id,
            (
                f"✅ Bienvenue <b>{traveler.first_name}</b>.\n"
                f"Votre compte est lié au voyageur <b>{traveler.public_id}</b>.\n\n"
                "Vous recevrez ici les rappels de suivi 21 jours, les alertes "
                "sanitaires importantes et les messages de l'INHP.\n\n"
                "Envoyez /stop à tout moment pour vous désabonner."
            ),
        )
        result["status"] = "linked" if created else "relinked"
        result["traveler_id"] = traveler.pk
        return result

    if command == "stop":
        updated = TelegramSubscription.objects.filter(
            chat_id=chat_id, is_active=True
        ).update(is_active=False)
        if updated:
            send_message(
                chat_id,
                "🔕 Abonnement désactivé. Vous ne recevrez plus de notifications "
                "de l'INHP par Telegram. Envoyez /start pour vous réabonner.",
            )
            result["status"] = "stopped"
        else:
            send_message(chat_id, "Aucun abonnement actif à désactiver.")
            result["status"] = "no_active_sub"
        return result

    if command == "help":
        send_message(
            chat_id,
            "<b>Commandes disponibles</b>\n"
            "• /start &lt;TRV-XXX&gt; — lier ce chat à votre voyageur\n"
            "• /link  &lt;TRV-XXX&gt; — re-lier (idem /start)\n"
            "• /stop — vous désabonner\n"
            "• /help — afficher cette aide\n\n"
            "Support : info@destinationci.com — 143",
        )
        result["status"] = "help"
        return result

    # Message libre — on trace juste last_message_at (utile pour purge)
    TelegramSubscription.objects.filter(chat_id=chat_id).update(
        last_message_at=timezone.now(),
    )
    result["status"] = "free_message_ignored"
    return result
