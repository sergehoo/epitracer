"""Tâches Celery liées aux pass : expiration, nettoyage des logs."""
from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .models import HealthPass, HealthPassStatus


@shared_task(name="passes.mark_expired_passes")
def mark_expired_passes() -> dict:
    qs = HealthPass.objects.filter(status=HealthPassStatus.ACTIVE, expires_at__lte=timezone.now())
    count = qs.update(status=HealthPassStatus.EXPIRED)
    return {"expired": count}
