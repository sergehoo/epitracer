"""Helpers pour créer/diffuser des alertes sanitaires."""
from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.contenttypes.models import ContentType

from .models import HealthAlert


def trigger_alert(
    *,
    code: str,
    title: str,
    description: str = "",
    severity: str = "info",
    disease=None,
    entry_point=None,
    target: Any | None = None,
    metadata: dict | None = None,
    triggered_by=None,
) -> HealthAlert:
    target_ct, target_id = (None, None)
    if target is not None:
        target_ct = ContentType.objects.get_for_model(target.__class__)
        target_id = str(getattr(target, "pk", ""))

    alert = HealthAlert.objects.create(
        code=code,
        title=title,
        description=description,
        severity=severity,
        disease=disease,
        entry_point=entry_point,
        target_ct=target_ct,
        target_id=target_id,
        metadata=metadata or {},
        triggered_by=triggered_by,
    )
    broadcast_alert(alert)
    return alert


def broadcast_alert(alert: HealthAlert) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    payload = {
        "type": "alert.message",
        "data": {
            "id": str(alert.uuid),
            "code": alert.code,
            "title": alert.title,
            "severity": alert.severity,
            "status": alert.status,
            "disease": alert.disease.code if alert.disease_id else None,
            "entry_point": alert.entry_point.name if alert.entry_point_id else None,
            "created_at": alert.created_at.isoformat(),
        },
    }
    async_to_sync(layer.group_send)("alerts", payload)
