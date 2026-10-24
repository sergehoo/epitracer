"""Tâches Celery du module quarantaine."""
from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.surveillance.services import trigger_alert

from .models import DailyCheck, QuarantineRecord, QuarantineStatus
from .services import close_quarantine


@shared_task(name="quarantine.send_daily_reminders")
def send_daily_reminders():
    """Alias historique → `companion.send_daily_checkin_reminders`.

    L'ancienne version envoyait un SMS par dossier de quarantaine, sans
    consentement ni idempotence (doublon avec le rappel companion si une
    ancienne PeriodicTask pointe encore ici). La délégation garantit un seul
    rappel par voyageur et par jour, sous la garde anti SMS pumping.
    """
    from apps.companion.tasks import send_daily_checkin_reminders

    return send_daily_checkin_reminders.run()


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
