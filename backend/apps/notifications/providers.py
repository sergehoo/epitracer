"""Providers d'envoi : abstraction permettant de brancher facilement Twilio, Orange, FCM, etc.

En l'absence de credentials, le provider 'stub' loggue le message — pratique en dev/CI.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("epidemitracker.notifications")


@dataclass
class SendResult:
    ok: bool
    provider: str
    provider_id: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# SMS
# ---------------------------------------------------------------------------
def send_sms(recipient: str, message: str) -> SendResult:
    provider = settings.NOTIFICATIONS["SMS_PROVIDER"]
    if provider == "twilio":
        sid = settings.NOTIFICATIONS["TWILIO_ACCOUNT_SID"]
        token = settings.NOTIFICATIONS["TWILIO_AUTH_TOKEN"]
        from_ = settings.NOTIFICATIONS["TWILIO_FROM_NUMBER"]
        if not (sid and token and from_):
            return SendResult(ok=False, provider="twilio", error="Twilio non configuré.")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        try:
            r = httpx.post(
                url, data={"From": from_, "To": recipient, "Body": message},
                auth=(sid, token), timeout=15,
            )
            r.raise_for_status()
            return SendResult(ok=True, provider="twilio", provider_id=r.json().get("sid", ""))
        except Exception as exc:
            return SendResult(ok=False, provider="twilio", error=str(exc))
    # stub par défaut
    logger.info("[SMS:stub] to=%s body=%s", recipient, message[:120])
    return SendResult(ok=True, provider="stub", provider_id="local")


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
def send_email(recipient: str, subject: str, body: str) -> SendResult:
    try:
        send_mail(
            subject=subject or "EpidemiTracker",
            message=body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=[recipient],
            fail_silently=False,
        )
        return SendResult(ok=True, provider="email")
    except Exception as exc:
        return SendResult(ok=False, provider="email", error=str(exc))


# ---------------------------------------------------------------------------
# WhatsApp (Twilio par défaut, sinon stub)
# ---------------------------------------------------------------------------
def send_whatsapp(recipient: str, message: str) -> SendResult:
    provider = settings.NOTIFICATIONS["WHATSAPP_PROVIDER"]
    if provider == "twilio":
        from_ = f"whatsapp:{settings.NOTIFICATIONS['WHATSAPP_FROM_NUMBER']}"
        to = f"whatsapp:{recipient}"
        sid = settings.NOTIFICATIONS["TWILIO_ACCOUNT_SID"]
        token = settings.NOTIFICATIONS["TWILIO_AUTH_TOKEN"]
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        try:
            r = httpx.post(url, data={"From": from_, "To": to, "Body": message},
                           auth=(sid, token), timeout=15)
            r.raise_for_status()
            return SendResult(ok=True, provider="twilio_whatsapp", provider_id=r.json().get("sid", ""))
        except Exception as exc:
            return SendResult(ok=False, provider="twilio_whatsapp", error=str(exc))
    logger.info("[WhatsApp:stub] to=%s body=%s", recipient, message[:120])
    return SendResult(ok=True, provider="stub", provider_id="local")


# ---------------------------------------------------------------------------
# Push (FCM)
# ---------------------------------------------------------------------------
def send_push(token: str, title: str, body: str) -> SendResult:
    key = settings.NOTIFICATIONS["FCM_SERVER_KEY"]
    if not key:
        logger.info("[Push:stub] token=%s title=%s body=%s", token[:12], title, body[:120])
        return SendResult(ok=True, provider="stub", provider_id="local")
    try:
        r = httpx.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={"Authorization": f"key={key}", "Content-Type": "application/json"},
            json={"to": token, "notification": {"title": title, "body": body}},
            timeout=15,
        )
        r.raise_for_status()
        return SendResult(ok=True, provider="fcm", provider_id=str(r.json().get("multicast_id", "")))
    except Exception as exc:
        return SendResult(ok=False, provider="fcm", error=str(exc))
