"""Helper d'audit pour les actions notifications."""
from __future__ import annotations

from typing import Optional

from apps.notifications.models import (
    Notification, NotificationAuditAction, NotificationAuditLog,
)


def _client_ip(request) -> Optional[str]:
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(
    *,
    notification: Notification,
    action: str,
    actor=None,
    request=None,
    metadata: Optional[dict] = None,
) -> NotificationAuditLog:
    """Enregistre une action d'audit sur une notification.

    Append-only : on ne modifie jamais une entrée existante.
    """
    return NotificationAuditLog.objects.create(
        notification=notification,
        actor=actor if (actor and getattr(actor, "is_authenticated", False)) else None,
        action=action,
        ip_address=_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "") if request else "")[:300],
        metadata=metadata or {},
    )


class Actions:
    """Alias court pour les valeurs choices."""
    CREATE = NotificationAuditAction.CREATE
    SEND = NotificationAuditAction.SEND
    RETRY = NotificationAuditAction.RETRY
    CANCEL = NotificationAuditAction.CANCEL
    DELIVERED = NotificationAuditAction.DELIVERED
    FAILED = NotificationAuditAction.FAILED
    VIEW = NotificationAuditAction.VIEW
