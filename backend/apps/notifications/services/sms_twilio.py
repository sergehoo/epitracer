"""Envoi SMS via Twilio (numéros internationaux hors +225)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger("epidemitracker.notifications.twilio")


@dataclass
class TwilioSendResult:
    ok: bool
    provider_message_id: str = ""
    error: str = ""
    raw_response: Optional[dict] = None


def _get_settings() -> dict:
    cfg = getattr(settings, "NOTIFICATIONS", {})
    return {
        "enabled": cfg.get("TWILIO_SMS_ENABLED", bool(cfg.get("TWILIO_ACCOUNT_SID"))),
        "account_sid": cfg.get("TWILIO_ACCOUNT_SID", ""),
        "auth_token": cfg.get("TWILIO_AUTH_TOKEN", ""),
        "from_number": cfg.get("TWILIO_FROM_NUMBER", ""),
        "timeout": int(cfg.get("TWILIO_TIMEOUT", 15)),
        "status_callback_base": cfg.get("TWILIO_STATUS_CALLBACK_BASE", ""),
    }


def send_sms(to: str, body: str, metadata: Optional[dict] = None) -> TwilioSendResult:
    """Envoie un SMS via Twilio.

    Args:
        to: numéro E.164 (+xxx...)
        body: contenu (jusqu'à ~1600 caractères pour multi-segments)
        metadata: peut contenir 'status_callback_path' (URL relative)
                  pour recevoir les webhooks de statut.
    """
    cfg = _get_settings()

    if not cfg["enabled"]:
        logger.info("[twilio STUB] to=%s body=%s", _mask(to), body[:80])
        return TwilioSendResult(ok=True, provider_message_id="stub-twilio")

    if not (cfg["account_sid"] and cfg["auth_token"] and cfg["from_number"]):
        return TwilioSendResult(
            ok=False, error="Twilio : credentials manquants.",
        )

    url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Messages.json"
    data = {"From": cfg["from_number"], "To": to, "Body": body}

    # Status callback (optionnel — webhook de delivery report)
    callback_base = (metadata or {}).get("status_callback_base") or cfg["status_callback_base"]
    if callback_base:
        data["StatusCallback"] = f"{callback_base.rstrip('/')}/api/webhooks/twilio/sms/status/"

    try:
        r = httpx.post(
            url,
            data=data,
            auth=(cfg["account_sid"], cfg["auth_token"]),
            timeout=cfg["timeout"],
        )
    except httpx.HTTPError as exc:
        logger.error("Twilio : HTTP error %s", exc)
        return TwilioSendResult(ok=False, error=f"Erreur réseau : {exc}")

    if not (200 <= r.status_code < 300):
        try:
            err = r.json().get("message") or r.text[:200]
        except Exception:  # noqa: BLE001
            err = r.text[:200]
        return TwilioSendResult(
            ok=False,
            error=f"Twilio HTTP {r.status_code} : {err}",
            raw_response={"status": r.status_code, "body": r.text[:500]},
        )

    body_data = r.json()
    return TwilioSendResult(
        ok=True,
        provider_message_id=body_data.get("sid", ""),
        raw_response=body_data,
    )


def _mask(phone: str) -> str:
    if not phone or len(phone) < 10:
        return phone or ""
    return phone[:6] + "****" + phone[-4:]
