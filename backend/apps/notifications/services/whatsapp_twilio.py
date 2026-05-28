"""Envoi WhatsApp via Twilio.

Doc : https://www.twilio.com/docs/whatsapp/api

Le numéro Twilio doit être préfixé par "whatsapp:" dans l'API.
Pour utiliser un template approuvé, on passe son SID via le param
`ContentSid` (et les variables via `ContentVariables`).
"""
from __future__ import annotations

import hmac
import json
import logging
from base64 import b64encode
from hashlib import sha1
from typing import Optional

import httpx
from django.conf import settings

from .whatsapp_base import (
    WhatsAppProviderBase, WhatsAppSendResult, WhatsAppStatusEvent,
)

logger = logging.getLogger("epidemitracker.notifications.whatsapp_twilio")


def _cfg() -> dict:
    c = getattr(settings, "NOTIFICATIONS", {})
    return {
        "account_sid": c.get("TWILIO_ACCOUNT_SID", ""),
        "auth_token": c.get("TWILIO_AUTH_TOKEN", ""),
        "from_number": (
            c.get("TWILIO_WHATSAPP_FROM")
            or c.get("WHATSAPP_FROM_NUMBER")
            or ""
        ),
        "timeout": int(c.get("WHATSAPP_TIMEOUT", 15)),
        "callback_base": c.get("TWILIO_STATUS_CALLBACK_BASE", ""),
        "enabled": c.get("WHATSAPP_ENABLED", False),
    }


class TwilioWhatsAppProvider(WhatsAppProviderBase):
    name = "twilio"

    # ── ENVOIS ──────────────────────────────────────────────────────
    def send_text(self, to: str, body: str) -> WhatsAppSendResult:
        cfg = _cfg()
        if not cfg["enabled"]:
            logger.info("[twilio_wa STUB] to=%s body=%s", _mask(to), body[:80])
            return WhatsAppSendResult(ok=True, provider_message_id="stub-twilio-wa")

        if not (cfg["account_sid"] and cfg["auth_token"] and cfg["from_number"]):
            return WhatsAppSendResult(ok=False, error="Twilio WhatsApp : credentials manquants.")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Messages.json"
        data = {
            "From": f"whatsapp:{cfg['from_number']}",
            "To": f"whatsapp:{to}",
            "Body": body,
        }
        if cfg["callback_base"]:
            data["StatusCallback"] = (
                f"{cfg['callback_base'].rstrip('/')}/api/v1/notifications/webhooks/twilio/whatsapp/status/"
            )

        try:
            r = httpx.post(
                url, data=data,
                auth=(cfg["account_sid"], cfg["auth_token"]),
                timeout=cfg["timeout"],
            )
        except httpx.HTTPError as exc:
            return WhatsAppSendResult(ok=False, error=f"Twilio WhatsApp réseau : {exc}")

        return self._parse_twilio_response(r)

    def send_template(
        self, to: str, template_code: str,
        variables: Optional[list] = None,
        language: str = "fr",
    ) -> WhatsAppSendResult:
        cfg = _cfg()
        if not cfg["enabled"]:
            logger.info("[twilio_wa STUB template] to=%s tpl=%s", _mask(to), template_code)
            return WhatsAppSendResult(ok=True, provider_message_id="stub-twilio-wa-tpl")

        if not (cfg["account_sid"] and cfg["auth_token"] and cfg["from_number"]):
            return WhatsAppSendResult(ok=False, error="Twilio WhatsApp : credentials manquants.")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Messages.json"
        data = {
            "From": f"whatsapp:{cfg['from_number']}",
            "To": f"whatsapp:{to}",
            # Twilio Content API : `ContentSid` est le HX... du template.
            # On suppose ici que `template_code` EST le ContentSid (HX...).
            "ContentSid": template_code,
        }
        if variables:
            # Twilio attend un JSON {"1": "valeur1", "2": "valeur2", ...}
            payload = {str(i + 1): str(v) for i, v in enumerate(variables)}
            data["ContentVariables"] = json.dumps(payload, ensure_ascii=False)
        if cfg["callback_base"]:
            data["StatusCallback"] = (
                f"{cfg['callback_base'].rstrip('/')}/api/v1/notifications/webhooks/twilio/whatsapp/status/"
            )

        try:
            r = httpx.post(
                url, data=data,
                auth=(cfg["account_sid"], cfg["auth_token"]),
                timeout=cfg["timeout"],
            )
        except httpx.HTTPError as exc:
            return WhatsAppSendResult(ok=False, error=f"Twilio WhatsApp réseau : {exc}")

        return self._parse_twilio_response(r)

    # ── WEBHOOKS ────────────────────────────────────────────────────
    def validate_webhook(self, request) -> bool:
        cfg = _cfg()
        token = cfg["auth_token"]
        if not token:
            return False
        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            return False
        url = request.build_absolute_uri().split("?")[0]
        params = sorted(request.data.items()) if hasattr(request.data, "items") else []
        data_to_sign = url + "".join(f"{k}{v}" for k, v in params)
        mac = hmac.new(token.encode(), data_to_sign.encode(), sha1)
        expected = b64encode(mac.digest()).decode()
        return hmac.compare_digest(expected, signature)

    def parse_status_webhook(self, payload) -> Optional[WhatsAppStatusEvent]:
        sid = payload.get("MessageSid") or payload.get("SmsSid")
        raw_status = (payload.get("MessageStatus") or payload.get("SmsStatus") or "").lower()
        if not (sid and raw_status):
            return None
        mapped = {
            "queued": "queued", "sent": "sent",
            "delivered": "delivered", "read": "read",
            "failed": "failed", "undelivered": "failed",
        }.get(raw_status, raw_status)
        return WhatsAppStatusEvent(
            provider_message_id=sid,
            status=mapped,
            error=f"code={payload.get('ErrorCode', '')}" if payload.get("ErrorCode") else "",
            raw_payload=dict(payload) if hasattr(payload, "items") else None,
        )

    # ── Helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _parse_twilio_response(r) -> WhatsAppSendResult:
        if not (200 <= r.status_code < 300):
            try:
                err = r.json().get("message") or r.text[:200]
            except Exception:  # noqa: BLE001
                err = r.text[:200]
            return WhatsAppSendResult(
                ok=False,
                error=f"Twilio WhatsApp HTTP {r.status_code} : {err}",
                raw_response={"status": r.status_code, "body": r.text[:500]},
            )
        try:
            body = r.json()
        except Exception:  # noqa: BLE001
            body = {}
        return WhatsAppSendResult(
            ok=True,
            provider_message_id=body.get("sid", ""),
            raw_response=body,
        )


def _mask(phone: str) -> str:
    if not phone or len(phone) < 10:
        return phone or ""
    return phone[:6] + "****" + phone[-4:]
