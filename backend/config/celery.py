"""Configuration Celery pour EpidemiTracker."""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging  # noqa: F401

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("epidemitracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ----------------------------------------------------------------------------
# Beat schedule — jobs périodiques.
#
# Note : `CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"`
# est défini dans settings, ce qui permet aussi de surcharger ces jobs depuis
# l'admin Django (PeriodicTask). Ce dict sert de SEED par défaut.
#
# Fuseau : Africa/Abidjan (= UTC) — voir DJANGO_TIME_ZONE.
# ----------------------------------------------------------------------------
app.conf.beat_schedule = {
    # Rappel quotidien à 08:00 heure locale Abidjan (= 08:00 UTC).
    "companion-daily-followup-reminders": {
        "task": "companion.send_daily_followup_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    # Détection des check-ins manqués toutes les 6 heures (à xx:15 pour
    # éviter le congestion à l'heure pile).
    "companion-detect-missed-checkins": {
        "task": "companion.detect_missed_checkins",
        "schedule": crontab(minute=15, hour="*/6"),
    },
    # Message de fin de période à 18:00 (laisser le temps au check-in du jour).
    "companion-send-completion-messages": {
        "task": "companion.send_completion_messages",
        "schedule": crontab(hour=18, minute=0),
    },
    # Nettoyage hebdomadaire des subscriptions HS le dimanche à 03:00.
    "companion-cleanup-stale-push-subscriptions": {
        "task": "companion.cleanup_stale_push_subscriptions",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
    # Purge RGPD hebdomadaire des voyageurs dont le suivi est clôturé > 30j.
    # Anonymisation + suppression des pings GPS. Dimanche à 03:30.
    "companion-purge-closed-followups": {
        "task": "companion.purge_closed_followups",
        "schedule": crontab(hour=3, minute=30, day_of_week=0),
    },
    # ---- Maintenance core ----
    # Backup PostgreSQL quotidien à 02:00 UTC. Préférer le cron host pour
    # plus de robustesse — voir scripts/backup_postgres.sh. La tâche Celery
    # est un fallback qui dépend de la présence de pg_dump dans le worker.
    "core-postgres-backup": {
        "task": "core.run_postgres_backup",
        "schedule": crontab(hour=2, minute=0),
    },
    # Rotation des audit logs > 5 ans, mensuel (1er du mois à 04:00).
    "core-rotate-audit-logs": {
        "task": "core.rotate_old_audit_logs",
        "schedule": crontab(day_of_month=1, hour=4, minute=0),
    },
}


@app.task(bind=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
