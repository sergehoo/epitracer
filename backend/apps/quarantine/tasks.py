"""Tâches Celery du module quarantaine."""
from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.notifications.tasks import send_notification
from apps.surveillance.services import trigger_alert

from .models import DailyCheck, QuarantineRecord, QuarantineStatus
from .services import close_quarantine


@shared_task(name="quarantine.send_daily_reminders")
def send_daily_reminders():
    """Envoie chaque matin une notification aux voyageurs sous quarantaine active."""
    active = QuarantineRecord.objects.filter(status=QuarantineStatus.ACTIVE)
    sent = 0
    for qr in active.iterator(chunk_size=500):
        traveler = qr.traveler
        if not (traveler.phone_mobile or traveler.email):
            continue
        send_notification.delay(
            channel="sms" if traveler.phone_mobile else "email",
            recipient=traveler.phone_mobile or traveler.email,
            template_code="quarantine_daily_reminder",
            context={
                "traveler_id": traveler.public_id,
                "day": (timezone.now().date() - qr.started_on).days,
            },
        )
        sent += 1
    return {"reminders_sent": sent}


@shared_task(name="quarantine.detect_missed_checks")
def detect_missed_checks(grace_hours: int = 36):
    """Déclenche une alerte si un voyageur n'a pas fait son check quotidien."""
    today = timezone.now().date()
    threshold = today - timedelta(days=1)
    qs = QuarantineRecord.objects.filter(status=QuarantineStatus.ACTIVE)
    raised = 0
    for qr in qs.iterator(chunk_size=500):
        last_check = qr.daily_checks.order_by("-check_date").first()
        if last_check is None or last_check.check_date < threshold:
            trigger_alert(
                code="quarantine_missed_check",
                title=f"Suivi manqué - {qr.traveler.public_id}",
                description=f"Aucun check depuis {grace_hours}h pour la quarantaine {qr.uuid}.",
                severity="medium",
                disease=qr.disease,
                target=qr,
            )
            raised += 1
    return {"alerts_raised": raised}


@shared_task(name="quarantine.auto_close_completed")
def auto_close_completed():
    """Clôt automatiquement les quarantaines arrivées au terme prévu."""
    today = timezone.now().date()
    qs = QuarantineRecord.objects.filter(status=QuarantineStatus.ACTIVE, expected_end_on__lte=today)
    closed = 0
    for qr in qs.iterator(chunk_size=500):
        close_quarantine(qr)
        closed += 1
    return {"closed": closed}
