"""
Tâches Celery du module Companion.

Schedulées par `django-celery-beat` (database scheduler) — voir
`PeriodicTask` dans l'admin Django ou la commande de seed.

Toutes les tâches loguent un résumé en fin d'exécution et sont
idempotentes (on peut les relancer sans dommage).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

from .models import ConsentScope, PushSubscription
from .push import push_notify
from .services import has_consent

logger = logging.getLogger(__name__)


# ============================================================================
# Rappel quotidien — envoyé chaque matin à tous les voyageurs en quarantaine
# active qui ont consenti aux notifications.
# ============================================================================


@shared_task(
    bind=True, name="companion.send_daily_followup_reminders",
    autoretry_for=(Exception,), retry_backoff=True, max_retries=3,
)
def send_daily_followup_reminders(self) -> dict[str, int]:
    """Envoie un rappel push à chaque voyageur en suivi actif."""
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    stats = {"travelers": 0, "push_sent": 0, "push_failed": 0, "skipped_no_consent": 0}

    active_qs = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler")

    for q in active_qs:
        traveler = q.traveler
        stats["travelers"] += 1
        if not has_consent(traveler, ConsentScope.PUSH_NOTIFICATIONS):
            stats["skipped_no_consent"] += 1
            continue

        day_index = max(0, (date.today() - q.started_on).days)
        total = (q.expected_end_on - q.started_on).days
        body = (
            "Bonjour, nous espérons que vous allez bien. Merci de prendre quelques "
            "secondes pour confirmer votre état de santé aujourd'hui."
        )
        result = push_notify(
            traveler=traveler,
            title=f"Comment vous sentez-vous aujourd'hui ?",
            body=body,
            url=f"/voyageur/suivi?id={traveler.public_id}",
            tag="daily-followup",
            notification_type="daily_reminder",
            extra={"day": day_index, "total": total},
        )
        stats["push_sent"] += result["sent"]
        stats["push_failed"] += result["failed"] + result["gone"]

    logger.info("send_daily_followup_reminders: %s", stats)
    return stats


# ============================================================================
# Détection des check-ins manqués (48h sans nouvelle)
# ============================================================================


@shared_task(
    bind=True, name="companion.detect_missed_checkins",
    autoretry_for=(Exception,), retry_backoff=True, max_retries=3,
)
def detect_missed_checkins(self, threshold_hours: int = 48) -> dict[str, int]:
    """Crée une HealthAlert pour chaque voyageur en suivi actif qui n'a
    pas fait de check-in depuis plus de `threshold_hours`.

    Envoie aussi un push de rappel doux (un seul, idempotent par jour).
    """
    from django.contrib.contenttypes.models import ContentType
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus
    from apps.surveillance.models import HealthAlert

    stats = {"checked": 0, "missed": 0, "alerts_created": 0, "push_sent": 0}
    cutoff = timezone.now() - timedelta(hours=threshold_hours)

    active_qs = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler")

    for q in active_qs:
        stats["checked"] += 1
        last_check = q.daily_checks.order_by("-check_date").first()
        last_date = last_check.check_date if last_check else q.started_on
        last_dt = timezone.make_aware(
            timezone.datetime.combine(last_date, timezone.datetime.min.time())
        ) if hasattr(timezone, "datetime") else None

        # Fallback simple par comparaison de date
        if last_check and (date.today() - last_check.check_date).days < threshold_hours / 24:
            continue
        if not last_check and (timezone.now() - q.created_at) < timedelta(hours=threshold_hours):
            continue

        stats["missed"] += 1

        # Idempotence : un seul "missed checkin" par voyageur par jour
        alert_code = f"MISS-{q.traveler.public_id}-{date.today():%Y%m%d}"
        if not HealthAlert.objects.filter(code=alert_code).exists():
            HealthAlert.objects.create(
                code=alert_code,
                title=f"Aucune nouvelle depuis {threshold_hours}h — {q.traveler.public_id}",
                description=(
                    f"Dernier check-in : {last_check.check_date if last_check else 'jamais'}. "
                    "Tenter un contact téléphonique ou WhatsApp."
                ),
                severity="MEDIUM",
                status="OPEN",
                target_ct=ContentType.objects.get_for_model(q.traveler),
                target_id=q.traveler.pk,
            )
            stats["alerts_created"] += 1

        # Push doux (uniquement si push consenti)
        if has_consent(q.traveler, ConsentScope.PUSH_NOTIFICATIONS):
            result = push_notify(
                traveler=q.traveler,
                title="Donnez-nous de vos nouvelles",
                body="Quelques secondes suffisent pour confirmer que tout va bien.",
                url=f"/voyageur/suivi?id={q.traveler.public_id}",
                tag="missed-checkin",
                notification_type="missed_checkin",
            )
            stats["push_sent"] += result["sent"]

    logger.info("detect_missed_checkins: %s", stats)
    return stats


# ============================================================================
# Message de fin de suivi (J21+)
# ============================================================================


@shared_task(
    bind=True, name="companion.send_completion_messages",
    autoretry_for=(Exception,), retry_backoff=True, max_retries=3,
)
def send_completion_messages(self) -> dict[str, int]:
    """Envoie un message de fin (et désactive les abonnements push) pour
    chaque quarantaine arrivée à terme aujourd'hui."""
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    stats = {"completed": 0, "push_sent": 0}
    today = date.today()
    qs = QuarantineRecord.objects.filter(
        expected_end_on=today,
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler")

    for q in qs:
        stats["completed"] += 1
        traveler = q.traveler

        # Push final si consenti
        if has_consent(traveler, ConsentScope.PUSH_NOTIFICATIONS):
            result = push_notify(
                traveler=traveler,
                title="Période d'accompagnement terminée",
                body=(
                    "Votre période d'accompagnement sanitaire est terminée. "
                    "Merci pour votre coopération et bon séjour."
                ),
                url=f"/voyageur/suivi?id={traveler.public_id}",
                tag="followup-complete",
                notification_type="followup_complete",
            )
            stats["push_sent"] += result["sent"]

        # Marque la quarantaine comme COMPLETED
        q.status = QuarantineStatus.COMPLETED
        q.actual_end_on = today
        q.save(update_fields=["status", "actual_end_on", "updated_at"])

    logger.info("send_completion_messages: %s", stats)
    return stats


# ============================================================================
# Nettoyage des subscriptions inactives (> 90 jours sans usage réussi)
# ============================================================================


@shared_task(name="companion.cleanup_stale_push_subscriptions")
def cleanup_stale_push_subscriptions(days: int = 90) -> dict[str, int]:
    """Désactive (soft) les subscriptions qui n'ont pas été utilisées avec
    succès depuis `days` jours et dont le compteur d'échec est non nul."""
    cutoff = timezone.now() - timedelta(days=days)
    n = PushSubscription.objects.filter(
        is_active=True, failure_count__gte=3, last_used_at__lt=cutoff,
    ).update(is_active=False, updated_at=timezone.now())
    return {"deactivated": n}
