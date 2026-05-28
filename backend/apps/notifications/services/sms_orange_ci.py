"""Envoi SMS via Orange Côte d'Ivoire — API SMS Bulk officielle.

Doc fournisseur : https://developer.orange.com/apis/sms-ci/
Authentification : OAuth 2.0 Client Credentials. Le token a une durée
de vie ; on le cache en mémoire process avec un buffer de sécurité.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from django.conf import settings

logger = logging.getLogger("epidemitracker.notifications.orange_ci")


@dataclass
class OrangeSendResult:
    ok: bool
    provider_message_id: str = ""
    error: str = ""
    raw_response: Optional[dict] = None


# ---------------------------------------------------------------------------
# Token cache (mémoire process — suffisant pour Celery workers)
# ---------------------------------------------------------------------------
_TOKEN_CACHE: dict = {"token": None, "expires_at": 0.0}
_TOKEN_TTL_BUFFER = 60  # secondes de marge avant expiration


def _get_settings() -> dict:
    """Récupère les settings Orange CI avec défauts safe."""
    cfg = getattr(settings, "NOTIFICATIONS", {})
    return {
        "enabled": cfg.get("ORANGE_CI_SMS_ENABLED", False),
        "base_url": cfg.get("ORANGE_CI_SMS_BASE_URL", "https://api.orange.com/smsmessaging/v1"),
        "token_url": cfg.get("ORANGE_CI_SMS_TOKEN_URL", "https://api.orange.com/oauth/v3/token"),
        "client_id": cfg.get("ORANGE_CI_SMS_CLIENT_ID", ""),
        "client_secret": cfg.get("ORANGE_CI_SMS_CLIENT_SECRET", ""),
        "sender_name": cfg.get("ORANGE_CI_SMS_SENDER_NAME", "EpiTrace"),
        "timeout": int(cfg.get("ORANGE_CI_SMS_TIMEOUT", 15)),
    }


def _get_access_token(force_refresh: bool = False) -> str:
    """Obtient un access token OAuth, avec cache mémoire."""
    cfg = _get_settings()
    if not (cfg["client_id"] and cfg["client_secret"]):
        raise RuntimeError("Orange CI : ORANGE_CI_SMS_CLIENT_ID/SECRET manquant(s).")

    now = time.time()
    if (
        not force_refresh
        and _TOKEN_CACHE["token"]
        and _TOKEN_CACHE["expires_at"] > now + _TOKEN_TTL_BUFFER
    ):
        return _TOKEN_CACHE["token"]

    # Demande d'un nouveau token (Client Credentials Grant)
    try:
        r = httpx.post(
            cfg["token_url"],
            data={"grant_type": "client_credentials"},
            auth=(cfg["client_id"], cfg["client_secret"]),
            headers={"Accept": "application/json"},
            timeout=cfg["timeout"],
        )
        r.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Orange CI : échec OAuth token ({exc})") from exc

    data = r.json()
    token = data.get("access_token")
    expires_in = int(data.get("expires_in", 3600))
    if not token:
        raise RuntimeError(f"Orange CI : réponse OAuth invalide ({data})")

    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = now + expires_in
    return token


# ---------------------------------------------------------------------------
# Envoi SMS
# ---------------------------------------------------------------------------
def send_sms(to: str, body: str, metadata: Optional[dict] = None) -> OrangeSendResult:
    """Envoie un SMS via Orange CI.

    Args:
        to: numéro destinataire au format E.164 (+225XXXXXXXXXX)
        body: contenu du message (max 160 caractères pour rester en 1 SMS)
        metadata: champs additionnels facultatifs (transaction_id, etc.)

    Returns:
        OrangeSendResult avec ok/provider_message_id/error.
    """
    cfg = _get_settings()

    if not cfg["enabled"]:
        # Mode stub — utile en dev/CI sans credentials
        logger.info("[orange_ci STUB] to=%s body=%s", _mask(to), body[:80])
        return OrangeSendResult(ok=True, provider_message_id="stub-orange-ci")

    if not to.startswith("+225"):
        return OrangeSendResult(
            ok=False,
            error=f"Orange CI : numéro non-CI rejeté ({_mask(to)}).",
        )

    # Acquisition token
    try:
        token = _get_access_token()
    except Exception as exc:  # noqa: BLE001
        logger.error("Orange CI : token KO — %s", exc)
        return OrangeSendResult(ok=False, error=str(exc))

    sender = f"tel:{cfg['sender_name']}" if cfg["sender_name"] else "tel:+225"
    # Endpoint Orange CI standard : outbound/{senderAddress}/requests
    url = f"{cfg['base_url']}/outbound/{sender}/requests"

    payload = {
        "outboundSMSMessageRequest": {
            "address": [f"tel:{to}"],
            "senderAddress": sender,
            "outboundSMSTextMessage": {"message": body[:1530]},  # 10 segments max
        }
    }

    try:
        r = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=cfg["timeout"],
        )
    except httpx.HTTPError as exc:
        logger.error("Orange CI : HTTP error %s", exc)
        return OrangeSendResult(ok=False, error=f"Erreur réseau : {exc}")

    if r.status_code == 401:
        # Token expiré entre temps — on retente une fois avec refresh
        try:
            token = _get_access_token(force_refresh=True)
            r = httpx.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=cfg["timeout"],
            )
        except Exception as exc:  # noqa: BLE001
            return OrangeSendResult(ok=False, error=f"Re-auth Orange CI échouée : {exc}")

    if not (200 <= r.status_code < 300):
        return OrangeSendResult(
            ok=False,
            error=f"Orange CI HTTP {r.status_code} : {r.text[:200]}",
            raw_response={"status": r.status_code, "body": r.text[:500]},
        )

    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    # L'API Orange retourne dans `resourceURL` ou `resourceReference.resourceURL`
    res = data.get("outboundSMSMessageRequest", data)
    provider_id = (
        res.get("resourceReference", {}).get("resourceURL", "")
        or res.get("resourceURL", "")
        or r.headers.get("location", "")
    )

    return OrangeSendResult(
        ok=True,
        provider_message_id=provider_id[:200],
        raw_response=data,
    )


def _mask(phone: str) -> str:
    if not phone or len(phone) < 10:
        return phone or ""
    return phone[:6] + "****" + phone[-4:]
