"""Helper pour journaliser des évènements d'audit depuis le code métier."""
from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType

from .models import AuditAction, AuditLog


def audit(
    request,
    *,
    action: str,
    summary: str,
    target: Any | None = None,
    payload: dict | None = None,
) -> AuditLog:
    actor = getattr(request, "user", None)
    if actor is not None and not getattr(actor, "is_authenticated", False):
        actor = None

    target_ct = None
    target_id = None
    if target is not None:
        target_ct = ContentType.objects.get_for_model(target.__class__)
        target_id = str(getattr(target, "pk", ""))

    return AuditLog.objects.create(
        actor=actor,
        action=action if action in AuditAction.values else AuditAction.OTHER,
        target_ct=target_ct,
        target_id=target_id,
        summary=summary[:255],
        payload=payload or {},
        ip_address=getattr(request, "audit_ip", None),
        user_agent=getattr(request, "audit_user_agent", "") or "",
        request_id=getattr(request, "audit_request_id", "") or "",
    )
