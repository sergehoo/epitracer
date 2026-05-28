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
from urllib.parse import quote

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
    """Récupère les settings Orange CI avec défauts safe.

    IMPORTANT — Format Orange CI OneAPI :
      - `senderAddress` doit être un MSISDN au format E.164 préfixé `tel:`
        (typiquement le numéro du contrat Orange, ex: tel:+2250709862860).
      - `senderName` (champ séparé !) reçoit le sender ID alphanumérique
        ("INHP") tel qu'il sera affiché chez le destinataire.

    Mettre le sender ID dans `senderAddress` (notre ancien bug) entraîne
    HTTP 201 Created mais le SMS n'est jamais routé par l'opérateur.
    """
    cfg = getattr(settings, "NOTIFICATIONS", {})
    return {
        "enabled": cfg.get("ORANGE_CI_SMS_ENABLED", False),
        "base_url": cfg.get("ORANGE_CI_SMS_BASE_URL", "https://api.orange.com/smsmessaging/v1/outbound/"),
        "token_url": cfg.get("ORANGE_CI_SMS_TOKEN_URL", "https://api.orange.com/oauth/v3/token"),
        "client_id": cfg.get("ORANGE_CI_SMS_CLIENT_ID", ""),
        "client_secret": cfg.get("ORANGE_CI_SMS_CLIENT_SECRET", ""),
        # MSISDN émetteur (E.164, sans le préfixe "tel:") — sert pour le
        # `senderAddress` ET pour le path URL.
        "sender_msisdn": cfg.get("ORANGE_CI_SMS_SENDER_MSISDN", ""),
        # Sender ID alphanumérique (texte affiché côté destinataire) — sert
        # pour `senderName`. Doit être validé par Orange Business CI.
        "sender_name": cfg.get("ORANGE_CI_SMS_SENDER_NAME", "INHP"),
        "timeout": int(cfg.get("ORANGE_CI_SMS_TIMEOUT", 15)),
        # URL publique du webhook qu'Orange CI appellera avec le delivery report.
        "callback_url": cfg.get("ORANGE_CI_SMS_CALLBACK_URL", ""),
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
def send_sms(
    to: str,
    body: str,
    metadata: Optional[dict] = None,
    callback_data: Optional[str] = None,
) -> OrangeSendResult:
    """Envoie un SMS via Orange CI.

    Args:
        to: numéro destinataire au format E.164 (+225XXXXXXXXXX)
        body: contenu du message (max 160 caractères pour rester en 1 SMS)
        metadata: champs additionnels facultatifs (transaction_id, etc.)
        callback_data: identifiant opaque (typiquement notif.id) renvoyé tel
            quel par Orange dans le delivery report. Permet à notre webhook
            de retrouver la Notification cible. Ignoré si pas de callback_url
            configurée.

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

    # ── Construction du senderAddress (MSISDN) ──
    # senderAddress DOIT être un numéro de téléphone E.164 préfixé "tel:".
    # Le sender ID alphanumérique ("INHP") va dans le champ senderName, PAS
    # dans senderAddress. Mettre "tel:INHP" entraîne HTTP 201 sans routage
    # réel du SMS chez l'opérateur (bug constaté en mai 2026).
    msisdn = (cfg.get("sender_msisdn") or "").strip()
    if not msisdn:
        return OrangeSendResult(
            ok=False,
            error=(
                "Orange CI : ORANGE_CI_SMS_SENDER_MSISDN non configuré. "
                "Renseigner le numéro Orange du contrat (ex: +2250709862860)."
            ),
        )
    if not msisdn.startswith("+"):
        msisdn = "+" + msisdn.lstrip("0")

    sender_address = f"tel:{msisdn}"

    # Endpoint Orange CI standard : outbound/{senderAddress}/requests
    base = cfg["base_url"].rstrip("/")
    if base.endswith("/outbound"):
        prefix = base
    else:
        prefix = f"{base}/outbound"

    # Le path accepte `tel:+225...` quasi tel-quel ; on garde `:` et `+`
    # non-encodés (Orange retourne ses propres resourceURL avec ces caractères
    # en clair dans le path : .../outbound/tel:+2250709862860/requests/<uuid>).
    url = f"{prefix}/{quote(sender_address, safe=':+')}/requests"

    payload = {
        "outboundSMSMessageRequest": {
            "address": [f"tel:{to}"],
            "senderAddress": sender_address,
            "outboundSMSTextMessage": {"message": body[:1530]},  # 10 segments max
        }
    }
    # senderName : sender ID alphanumérique (5-11 chars), à valider chez Orange.
    if cfg.get("sender_name"):
        payload["outboundSMSMessageRequest"]["senderName"] = cfg["sender_name"][:11]

    # ── receiptRequest : indispensable pour qu'Orange nous renvoie le
    # delivery report. Sans cette section, le statut reste figé à `sent`
    # côté backend même si l'opérateur acquitte / rejette le message.
    if cfg.get("callback_url"):
        payload["outboundSMSMessageRequest"]["receiptRequest"] = {
            "notifyURL": cfg["callback_url"],
            "callbackData": str(callback_data or ""),
        }

    # Log au niveau DEBUG pour pouvoir tracer en cas d'incident (sans secrets)
    logger.debug("Orange CI POST %s payload=%s", url, payload)

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
