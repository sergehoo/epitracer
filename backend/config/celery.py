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
    # Rappel quotidien check-in à 08:00 heure locale Abidjan (= 08:00 UTC).
    # NB : ce job remplace l'ancien `send_daily_followup_reminders`, qui
    # subsiste comme alias pour ne pas casser les anciennes PeriodicTask
    # en base. Tous les nouveaux déploiements pointent sur le nom
    # `send_daily_checkin_reminders`.
    "companion-daily-checkin": {
        "task": "companion.send_daily_checkin_reminders",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "notifications"},
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
    # ---- Phase 9A : suivi médical complet ----
    # Vérifie toutes les 6 h que les voyageurs en suivi actif partagent
    # bien leur géoloc (Option 3 — RGPD-safe). Déclenche une `HealthAlert`
    # si absence de ping > N heures (N = protocol.geolocation_alert_after_hours,
    # 24 h par défaut), avec anti-spam de 24 h via
    # QuarantineRecord.geolocation_alert_raised_at.
    "medical-check-geolocation-compliance": {
        "task": "medical.check_geolocation_compliance_all",
        "schedule": crontab(minute=20, hour="*/6"),
        "options": {"queue": "quarantine"},
    },
    # ---- Phase 9D : automatisation du suivi sanitaire ----
    # Rappel quotidien protocole-aware à 08:00 — délègue à companion pour
    # les canaux et enrichit la timeline médicale (FollowUpAction +
    # DailyCheck.notification_sent). Tourne 5 minutes après companion pour
    # éviter une race condition sur l'horaire pile.
    "medical-send-daily-followup-reminders": {
        "task": "medical.send_daily_followup_reminders",
        "schedule": crontab(hour=8, minute=5),
        "options": {"queue": "quarantine"},
    },
    # Détection des check-ins manqués (statut MISSED) tous les soirs 23:00.
    # Déclenche l'escalade si N missed consécutifs (selon protocol).
    "medical-mark-missed-checkins": {
        "task": "medical.mark_missed_checkins",
        "schedule": crontab(hour=23, minute=0),
        "options": {"queue": "quarantine"},
    },
    # Filet de sécurité de l'escalade symptômes critiques : toutes les 30 min
    # en backup du signal `post_save MedicalSymptomReport(is_critical=True)`.
    # Re-scanne la dernière heure et ré-essaie les cas qui n'auraient pas
    # été escaladés par le signal (worker indisponible, etc.).
    "medical-escalate-critical-symptoms-backup": {
        "task": "medical.escalate_critical_symptoms",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "quarantine"},
    },
    # Clôture automatique des suivis arrivés à terme sans incident à 00:10.
    # Génère le PDF d'attestation MSHPCMU/INHP et notifie le voyageur.
    "medical-auto-close-completed-followups": {
        "task": "medical.auto_close_completed_followups",
        "schedule": crontab(hour=0, minute=10),
        "options": {"queue": "quarantine"},
    },
    # ─── Rapports hebdomadaires automatisés (apps.reports) ─────────────
    # Lundi 08:00 heure Africa/Abidjan (= UTC, cf. DJANGO_TIME_ZONE).
    # Génère + envoie par email + SMS aux destinataires actifs.
    # Idempotent : safe même si Beat déclenche 2x le même schedule.
    # Superadmin peut désactiver via AutomatedReportSchedule.is_active=False
    # (le task dispatch skip s'il n'y a pas de schedule actif).
    "reports-weekly-dispatch": {
        "task": "reports.dispatch_weekly_report",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
        "options": {"queue": "reports"},
    },
    # Retry des envois FAILED toutes les 15 minutes (backoff exponentiel
    # géré dans le task lui-même : 5min → 10min → 20min → PERMANENT).
    "reports-retry-failed-deliveries": {
        "task": "reports.retry_failed_weekly_reports",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "notifications"},
    },
    # Purge des fichiers PDF/Excel > 90 jours chaque dimanche 04:00.
    # Garde la ligne GeneratedReport + summary_data — libère uniquement
    # le stockage FileField.
    "reports-cleanup-expired-files": {
        "task": "reports.cleanup_expired_report_files",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),
        "options": {"queue": "reports"},
    },
}


@app.task(bind=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
