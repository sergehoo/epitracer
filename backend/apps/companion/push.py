"""
Service Web Push (VAPID, RFC 8030 + RFC 8292).

Centralise toute l'envoi de notifications PUSH vers les abonnés
`PushSubscription`. Utilisé par les tâches Celery et (optionnellement)
par des actions admin.

Le format du payload envoyé au navigateur est un JSON simple :

    {
      "title": "Comment vous sentez-vous ?",
      "body":  "Prenez un moment pour nous donner de vos nouvelles.",
      "url":   "/voyageur/suivi?id=TRV-XXXX",
      "tag":   "daily-followup",
      "type":  "daily_reminder"
    }

Le service worker se charge ensuite de l'affichage (icône, action,
redirection au clic). Cf. `frontend/public/sw.js`.
"""
from __future__ import annotations

import base64
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from django.conf import settings

from .models import PushSubscription

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Chargement des clés VAPID
# ----------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_private_key_pem() -> str:
    """Lit la clé privée VAPID (PEM, format SEC1 / PKCS#8)."""
    path = Path(settings.WEBPUSH["VAPID_PRIVATE_KEY_PATH"])
    if not path.exists():
        raise RuntimeError(
            f"Clé privée VAPID introuvable à {path}. "
            "Lancez `python manage.py generate_vapid_keys`."
        )
    return path.read_text()


@lru_cache(maxsize=1)
def get_vapid_public_key_b64url() -> str:
    """Retourne la clé publique VAPID en base64url (sans padding), format
    accepté par `pushManager.subscribe({applicationServerKey})` côté navigateur.

    Convertit la clé PEM publique (X.509 / SubjectPublicKeyInfo) en
    point P-256 non compressé (65 octets : 0x04 || X(32) || Y(32))
    encodé en base64url-without-padding.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey

    pub_path = Path(settings.WEBPUSH["VAPID_PUBLIC_KEY_PATH"])
    if not pub_path.exists():
        raise RuntimeError(
            f"Clé publique VAPID introuvable à {pub_path}. "
            "Lancez `python manage.py generate_vapid_keys`."
        )
    pub_key = serialization.load_pem_public_key(pub_path.read_bytes())
    if not isinstance(pub_key, EllipticCurvePublicKey):
        raise RuntimeError("La clé VAPID doit être ECDSA P-256.")
    raw = pub_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# ----------------------------------------------------------------------------
# Envoi
# ----------------------------------------------------------------------------


def _build_subscription_info(sub: PushSubscription) -> dict[str, Any]:
    """Format attendu par pywebpush.webpush()."""
    return {
        "endpoint": sub.endpoint,
        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
    }


def send_push_to_subscription(
    sub: PushSubscription, payload: dict[str, Any], ttl: int = 60 * 60,
) -> tuple[bool, str]:
    """Envoie un payload JSON à un seul abonnement.

    Retourne (success, info_message). Gère les erreurs courantes :
    - 404 / 410 → endpoint invalide → désactivation auto de la subscription ;
    - autre erreur → incrément du compteur d'échec (5 strikes → désactivation).
    """
    try:
        from pywebpush import WebPushException, webpush  # noqa: WPS433
    except ImportError:  # pragma: no cover
        return False, "pywebpush_not_installed"

    try:
        webpush(
            subscription_info=_build_subscription_info(sub),
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=_load_private_key_pem(),
            vapid_claims={"sub": settings.WEBPUSH["VAPID_CLAIM_SUB"]},
            ttl=ttl,
        )
        sub.mark_success()
        return True, "ok"
    except WebPushException as exc:  # type: ignore[misc]
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (404, 410):
            # Subscription expirée côté push service → désactiver
            sub.is_active = False
            sub.save(update_fields=["is_active", "updated_at"])
            return False, "gone"
        sub.mark_failure(error=str(exc)[:200])
        return False, f"webpush_error:{status_code}"
    except Exception as exc:  # noqa: BLE001 — best-effort logging
        logger.exception("Erreur inattendue lors de l'envoi push pour %s", sub.endpoint[:50])
        sub.mark_failure(error=str(exc)[:200])
        return False, "unexpected_error"


def push_notify(
    *,
    traveler,
    title: str,
    body: str,
    url: str = "/voyageur/suivi",
    tag: str = "epitrace",
    notification_type: str = "generic",
    extra: Optional[dict[str, Any]] = None,
    fallback_to_sms: bool = True,
    fallback_to_whatsapp: bool = False,
) -> dict[str, Any]:
    """Envoie un push à tous les abonnements ACTIFS d'un voyageur.

    Si aucune subscription active OU si toutes échouent, retombe sur SMS
    (ou WhatsApp si flag activé) via apps.notifications — uniquement si
    le voyageur a un numéro de téléphone enregistré ET un consentement
    explicite au scope `push` (qui couvre toutes les formes de rappel).

    Retourne un dict de stats : {sent, failed, gone, sms_sent}.
    """
    payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "url": url,
        "tag": tag,
        "type": notification_type,
    }
    if extra:
        payload.update(extra)

    stats = {"sent": 0, "failed": 0, "gone": 0, "sms_sent": 0, "whatsapp_sent": 0}
    subs = PushSubscription.objects.filter(traveler=traveler, is_active=True)
    for sub in subs:
        ok, info = send_push_to_subscription(sub, payload)
        if ok:
            stats["sent"] += 1
        elif info == "gone":
            stats["gone"] += 1
        else:
            stats["failed"] += 1

    # ---- Fallback SMS / WhatsApp ----
    # Critères : (0 push délivré) ET (numéro disponible) ET (consentement push actif)
    push_delivered = stats["sent"] > 0
    if push_delivered:
        return stats

    # Import différé pour éviter cycle / dépendance dure
    from .models import ConsentScope
    from .services import has_consent
    if not has_consent(traveler, ConsentScope.PUSH_NOTIFICATIONS):
        return stats

    # Texte SMS dérivé : on combine title + body, et on append l'URL absolue.
    short_text = f"{title}\n{body}"
    # Construire l'URL absolue (best-effort) : on utilise DESTINATION_BASE_URL si défini.
    from django.conf import settings
    base = getattr(settings, "PUBLIC_BASE_URL", "https://destinationci.com")
    short_text = f"{short_text}\n{base}{url}"[:480]

    try:
        from apps.notifications.tasks import send_notification  # noqa: WPS433
        if fallback_to_sms and traveler.phone_mobile:
            send_notification.delay(  # type: ignore[attr-defined]
                channel="sms", recipient=traveler.phone_mobile, body=short_text,
                context={"traveler_id": traveler.public_id, "type": notification_type},
            )
            stats["sms_sent"] += 1
        if fallback_to_whatsapp and getattr(traveler, "whatsapp_phone", "") and traveler.whatsapp_phone:
            send_notification.delay(  # type: ignore[attr-defined]
                channel="whatsapp", recipient=traveler.whatsapp_phone, body=short_text,
                context={"traveler_id": traveler.public_id, "type": notification_type},
            )
            stats["whatsapp_sent"] += 1
    except Exception:  # noqa: BLE001 — best-effort
        logger.exception("Échec fallback SMS/WhatsApp pour %s", traveler.public_id)

    return stats
