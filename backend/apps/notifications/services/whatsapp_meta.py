"""Envoi WhatsApp via Meta Cloud API (Graph API v19+).

Doc : https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages

Endpoint : POST https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages
Auth     : Bearer {META_WHATSAPP_TOKEN}

Webhook : Meta envoie un POST JSON sur l'endpoint configuré dans la
console développeur. Il faut répondre 200 OK rapidement.
Vérification : X-Hub-Signature-256 = HMAC-SHA256 (secret défini côté Meta).
"""
from __future__ import annotations

import hmac
import json
import logging
from hashlib import sha256
from typing import Optional

import httpx
from django.conf import settings

from .whatsapp_base import (
    WhatsAppProviderBase, WhatsAppSendResult, WhatsAppStatusEvent,
)

logger = logging.getLogger("epidemitracker.notifications.whatsapp_meta")


def _cfg() -> dict:
    c = getattr(settings, "NOTIFICATIONS", {})
    return {
        "enabled": c.get("WHATSAPP_ENABLED", False),
        "token": c.get("META_WHATSAPP_TOKEN", ""),
        "phone_number_id": c.get("META_WHATSAPP_PHONE_NUMBER_ID", ""),
        "business_id": c.get("META_WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
        "verify_token": c.get("META_WHATSAPP_VERIFY_TOKEN", ""),
        "app_secret": c.get("META_WHATSAPP_APP_SECRET", ""),
        "timeout": int(c.get("WHATSAPP_TIMEOUT", 15)),
        "api_version": c.get("META_WHATSAPP_API_VERSION", "v19.0"),
    }


class MetaWhatsAppProvider(WhatsAppProviderBase):
    name = "meta_whatsapp"

    # ── ENVOIS ──────────────────────────────────────────────────────
    def send_text(self, to: str, body: str) -> WhatsAppSendResult:
        cfg = _cfg()
        if not cfg["enabled"]:
            logger.info("[meta_wa STUB] to=%s body=%s", _mask(to), body[:80])
            return WhatsAppSendResult(ok=True, provider_message_id="stub-meta-wa")

        if not (cfg["token"] and cfg["phone_number_id"]):
            return WhatsAppSendResult(
                ok=False, error="Meta WhatsApp : token ou phone_number_id manquant.",
            )

        url = f"https://graph.facebook.com/{cfg['api_version']}/{cfg['phone_number_id']}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            # Meta veut le numéro SANS le "+" initial
            "to": to.lstrip("+"),
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        return self._post(url, cfg["token"], payload, cfg["timeout"])

    def send_template(
        self, to: str, template_code: str,
        variables: Optional[list] = None,
        language: str = "fr",
    ) -> WhatsAppSendResult:
        cfg = _cfg()
        if not cfg["enabled"]:
            logger.info("[meta_wa STUB template] to=%s tpl=%s", _mask(to), template_code)
            return WhatsAppSendResult(ok=True, provider_message_id="stub-meta-wa-tpl")

        if not (cfg["token"] and cfg["phone_number_id"]):
            return WhatsAppSendResult(
                ok=False, error="Meta WhatsApp : token ou phone_number_id manquant.",
            )

        # Construit le composant body avec les variables ordonnées
        components = []
        if variables:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(v)} for v in variables
                ],
            })

        url = f"https://graph.facebook.com/{cfg['api_version']}/{cfg['phone_number_id']}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "template",
            "template": {
                "name": template_code,
                "language": {"code": language},
                **({"components": components} if components else {}),
            },
        }
        return self._post(url, cfg["token"], payload, cfg["timeout"])

    # ── WEBHOOKS ────────────────────────────────────────────────────
    def validate_webhook(self, request) -> bool:
        """Vérifie X-Hub-Signature-256 = sha256(app_secret + raw_body)."""
        cfg = _cfg()
        secret = cfg["app_secret"]
        if not secret:
            # Si pas de secret configuré, on accepte (mais on loggue)
            logger.warning("Meta webhook : META_WHATSAPP_APP_SECRET manquant — validation skippée.")
            return True
        sig_header = request.headers.get("X-Hub-Signature-256", "")
        if not sig_header.startswith("sha256="):
            return False
        expected = sig_header[len("sha256="):]
        raw_body = request.body if hasattr(request, "body") else b""
        mac = hmac.new(secret.encode(), raw_body, sha256).hexdigest()
        return hmac.compare_digest(mac, expected)

    def parse_status_webhook(self, payload) -> Optional[WhatsAppStatusEvent]:
        """Format Meta : entry[].changes[].value.statuses[].

        Exemple :
            {
              "entry": [{
                "changes": [{
                  "value": {
                    "statuses": [{
                      "id": "wamid.xxxxx",
                      "status": "delivered",
                      "timestamp": "1234567890",
                      "errors": [{"code": ..., "title": "..."}]
                    }]
                  }
                }]
              }]
            }
        """
        if not isinstance(payload, dict):
            return None
        for entry in payload.get("entry", []) or []:
            for change in entry.get("changes", []) or []:
                value = change.get("value", {}) or {}
                for st in value.get("statuses", []) or []:
                    raw_status = (st.get("status") or "").lower()
                    mapped = {
                        "sent": "sent", "delivered": "delivered",
                        "read": "read", "failed": "failed",
                    }.get(raw_status, raw_status)
                    err_msg = ""
                    if st.get("errors"):
                        errs = st["errors"]
                        if isinstance(errs, list) and errs:
                            e0 = errs[0]
                            err_msg = f"code={e0.get('code')} : {e0.get('title') or e0.get('message') or ''}"
                    return WhatsAppStatusEvent(
                        provider_message_id=st.get("id", ""),
                        status=mapped,
                        timestamp=st.get("timestamp"),
                        error=err_msg,
                        raw_payload=payload,
                    )
        return None

    # ── Helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _post(url: str, token: str, payload: dict, timeout: int) -> WhatsAppSendResult:
        try:
            r = httpx.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            return WhatsAppSendResult(ok=False, error=f"Meta WhatsApp réseau : {exc}")

        if not (200 <= r.status_code < 300):
            try:
                err_data = r.json().get("error", {})
                err = err_data.get("message") or r.text[:200]
                code = err_data.get("code", "")
                full_err = f"Meta HTTP {r.status_code} ({code}) : {err}"
            except Exception:  # noqa: BLE001
                full_err = f"Meta HTTP {r.status_code} : {r.text[:200]}"
            return WhatsAppSendResult(
                ok=False, error=full_err,
                raw_response={"status": r.status_code, "body": r.text[:500]},
            )

        try:
            body = r.json()
        except Exception:  # noqa: BLE001
            body = {}
        # Meta retourne messages[0].id = "wamid.xxxxx"
        msgs = body.get("messages", []) or []
        msg_id = msgs[0].get("id", "") if msgs else ""
        return WhatsAppSendResult(
            ok=True, provider_message_id=msg_id, raw_response=body,
        )


def _mask(phone: str) -> str:
    if not phone or len(phone) < 10:
        return phone or ""
    return phone[:6] + "****" + phone[-4:]
