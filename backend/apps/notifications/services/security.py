"""Journal des événements suspects SMS + alertes administrateur.

`log_security_event()` est sûr sous attaque : une clé `dedupe` limite
l'écriture à un événement par fenêtre (les répétitions sont seulement
comptées dans le cache), pour ne pas transformer un flood en flood de base.
"""

from __future__ import annotations

import logging

from django.core.cache import cache
from django.db.models import TextChoices

from apps.core.ratelimit import fingerprint

logger = logging.getLogger("epidemitracker.security.sms")


class SecurityEventKind(TextChoices):
    RATE_LIMITED = "rate_limited"
    NUMBER_QUOTA = "number_quota_exceeded"
    TRAVELER_QUOTA = "traveler_quota_exceeded"
    PROVIDER_CAP = "provider_cap_reached"
    BUDGET_ALERT = "budget_alert"
    BUDGET_EXCEEDED = "budget_exceeded"
    URGENT_CAP = "urgent_cap_reached"
    SPIKE = "traffic_spike"
    TURNSTILE_FAILED = "turnstile_failed"
    OTP_REPLAY = "otp_replay"
    RECIPIENT_REJECTED = "recipient_rejected"
    ROUTING_BLOCKED = "routing_blocked"
    COUNTRY_BLOCKED = "country_blocked"


_CRITICAL = {
    SecurityEventKind.BUDGET_EXCEEDED,
    SecurityEventKind.SPIKE,
    SecurityEventKind.URGENT_CAP,
    SecurityEventKind.PROVIDER_CAP,
}
_INFO = {SecurityEventKind.RATE_LIMITED}


def mask_phone(phone: str) -> str:
    if not phone or len(phone) < 8:
        return phone or ""
    return phone[:6] + "****" + phone[-2:]


def log_security_event(
    kind: str,
    *,
    source: str = "",
    ip: str | None = None,
    phone: str = "",
    traveler=None,
    user=None,
    details: dict | None = None,
    dedupe: str | None = None,
    dedupe_window: int = 600,
):
    """Enregistre un événement (au plus un par `dedupe` et par fenêtre)."""
    from apps.notifications.models import SecurityEventSeverity, SmsSecurityEvent

    if dedupe:
        key = f"secevt:{kind}:{fingerprint(dedupe)}"
        if cache.add(key, 1, timeout=dedupe_window) is False:
            try:
                cache.incr(key)
            except ValueError:
                pass
            return None

    severity = (
        SecurityEventSeverity.CRITICAL
        if kind in _CRITICAL
        else SecurityEventSeverity.INFO
        if kind in _INFO
        else SecurityEventSeverity.WARNING
    )
    logger.warning(
        "SMS security event %s source=%s ip=%s phone=%s details=%s",
        kind,
        source,
        ip or "-",
        mask_phone(phone),
        details or {},
    )
    try:
        return SmsSecurityEvent.objects.create(
            kind=kind,
            severity=severity,
            source=source[:60],
            ip_address=ip or None,
            phone_hash=fingerprint(phone) if phone else "",
            phone_masked=mask_phone(phone),
            traveler=traveler if getattr(traveler, "pk", None) else None,
            user=user if getattr(user, "is_authenticated", False) else None,
            details=details or {},
        )
    except Exception:  # noqa: BLE001 — la journalisation ne bloque jamais le flux
        logger.exception("Événement de sécurité %s non enregistré", kind)
        return None


def admin_emails() -> list[str]:
    from django.contrib.auth import get_user_model

    from apps.accounts.models import RoleCode

    user_model = get_user_model()
    qs = (
        user_model.objects.filter(is_active=True)
        .filter(
            role_assignments__is_active=True,
            role_assignments__role__code=RoleCode.NATIONAL_ADMIN,
        )
        .exclude(email="")
    )
    return sorted(set(qs.values_list("email", flat=True)))


def alert_admins(
    subject: str, body: str, *, kind: str, once_key: str | None = None, once_window: int = 3600
) -> int:
    """Email aux administrateurs nationaux (une fois par `once_key`/fenêtre)."""
    from apps.notifications.models import MessageType

    from .dispatcher import enqueue_notification

    if (
        once_key
        and cache.add(f"adminalert:{fingerprint(once_key)}", 1, timeout=once_window) is False
    ):
        return 0
    sent = 0
    for email in admin_emails():
        try:
            res = enqueue_notification(
                channel="email",
                recipient=email,
                subject=subject,
                body=body,
                message_type=MessageType.ADMIN_NOTICE,
                metadata={"kind": kind},
            )
            sent += int(bool(res.ok))
        except Exception:  # noqa: BLE001 — une alerte ne casse jamais l'envoi
            logger.exception("Alerte admin %s non envoyée à %s", kind, email)
    return sent
