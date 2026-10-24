"""Emails des rapports : le statut affiché doit être le résultat réel d'envoi.

Constat (24/10/2026) : rapport hebdomadaire « Envoyé » à tous les destinataires
dans /notifications et /rapports, mais jamais reçu. Causes :
  - la notification email passait « Envoyée » dès la mise en file d'un second
    job (EmailLog), avant toute tentative SMTP ;
  - le journal d'envoi du rapport faisait de même ;
  - les rapports internes partaient par le profil PUBLIC (Amazon SES) ;
  - la file Celery « reports » (rapport automatique du lundi) n'était
    consommée par aucun worker.
Aucun serveur SMTP réel : la connexion est remplacée par le backend mémoire
ou par une connexion qui échoue.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core import mail
from django.core.mail import get_connection
from django.utils import timezone

from apps.notifications.email_models import EmailLog, EmailStatus, SenderProfile
from apps.notifications.models import Channel, MessageType, Notification, NotificationStatus
from apps.notifications.services.errors import ErrorCode
from apps.notifications.tasks import _execute_send

SES_SANDBOX_ERROR = (
    "(554, b'Message rejected: Email address is not verified. The following "
    "identities failed the check in region EU-WEST-1: dg@inhp.ci')"
)


class _FailingConnection:
    """Connexion SMTP qui lève l'erreur fournie à l'envoi."""

    def __init__(self, error: Exception):
        self.error = error

    def send_messages(self, messages):
        raise self.error

    def open(self):
        return True

    def close(self):
        return None


@pytest.fixture
def smtp(monkeypatch):
    """Remplace la connexion SMTP du routeur ; mémorise le profil utilisé."""
    state = {"profiles": [], "error": None}

    def build(profile_code):
        state["profiles"].append(profile_code)
        if state["error"] is not None:
            return _FailingConnection(state["error"])
        return get_connection("django.core.mail.backends.locmem.EmailBackend")

    monkeypatch.setattr("apps.notifications.services.email_router._build_connection", build)
    # Comme en production (Celery asynchrone) : un email seulement mis en file
    # n'est PAS envoyé. Les tests vérifient que rien ne repose sur cette file.
    state["queued"] = []
    monkeypatch.setattr(
        "apps.notifications.tasks_email.send_email_task.delay",
        lambda log_id: state["queued"].append(log_id),
    )
    return state


def _email_notif(**kw) -> Notification:
    defaults = dict(
        channel=Channel.EMAIL, recipient="dg@inhp.ci", subject="[EpiTrace] Rapport hebdomadaire",
        body="<!DOCTYPE html><html><head><title>Rapport</title></head><body>OK</body></html>",
        provider="smtp", status=NotificationStatus.QUEUED, message_type=MessageType.ADMIN_NOTICE,
        metadata={"kind": "weekly_report"},
    )
    defaults.update(kw)
    return Notification.objects.create(**defaults)


@pytest.mark.django_db
class TestNotificationEmail:
    def test_smtp_refusal_marks_the_notification_failed(self, smtp):
        smtp["error"] = Exception(SES_SANDBOX_ERROR)
        notif = _email_notif()

        ok, _, err = _execute_send(notif)

        notif.refresh_from_db()
        assert ok is False
        assert notif.status == NotificationStatus.FAILED
        assert notif.error_code == ErrorCode.EMAIL_UNVERIFIED  # erreur définitive
        log = EmailLog.objects.get()
        assert log.status == EmailStatus.FAILED and "not verified" in log.error_message
        assert notif.metadata["email_log_id"] == log.id
        assert smtp["queued"] == []  # tentative SMTP réelle, pas une mise en file

    def test_success_is_reported_only_after_smtp_acceptance(self, smtp):
        notif = _email_notif()
        ok, msg_id, _ = _execute_send(notif)

        notif.refresh_from_db()
        assert ok and notif.status == NotificationStatus.SENT
        assert len(mail.outbox) == 1
        assert EmailLog.objects.get().status == EmailStatus.SENT
        assert msg_id == f"emaillog:{EmailLog.objects.get().id}"
        assert smtp["queued"] == []

    def test_internal_mail_uses_internal_sender_and_traveler_mail_public(self, smtp):
        _execute_send(_email_notif())
        _execute_send(_email_notif(
            recipient="voyageur@example.com", message_type=MessageType.MANUAL_MESSAGE,
            metadata={}, body="Bonjour",
        ))

        assert smtp["profiles"] == ["internal", "public"]
        internal = SenderProfile.objects.get(code="internal").from_address
        public = SenderProfile.objects.get(code="public").from_address
        assert internal in mail.outbox[0].from_email
        assert public in mail.outbox[1].from_email

    def test_retry_reuses_the_same_email_log(self, smtp):
        smtp["error"] = OSError("Connection refused")  # transitoire → réessayable
        notif = _email_notif()
        _execute_send(notif)
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.FAILED
        assert notif.error_code == ErrorCode.NETWORK

        smtp["error"] = None
        _execute_send(notif)
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.SENT
        assert EmailLog.objects.count() == 1
        assert EmailLog.objects.get().status == EmailStatus.SENT


@pytest.mark.django_db
class TestWeeklyReportDelivery:
    @pytest.fixture
    def report(self):
        from apps.reports.models import (
            AutomatedReportRecipient,
            GeneratedReport,
            PreferredChannel,
            ReportStatus,
            ReportType,
        )

        AutomatedReportRecipient.objects.create(
            full_name="Directeur INHP", email="dg@inhp.ci",
            preferred_channel=PreferredChannel.EMAIL, consent_date=date.today(),
        )
        midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start = midnight - timedelta(days=7)
        return GeneratedReport.objects.create(
            report_type=ReportType.WEEKLY, period_start=start,
            period_end=start + timedelta(days=6, hours=23, minutes=59), status=ReportStatus.READY,
            summary_data={},
        )

    def _send(self, report):
        from apps.reports.tasks import send_weekly_report_email

        return send_weekly_report_email.apply(args=[report.pk]).result

    def test_rejected_report_email_is_shown_as_failed(self, smtp, report):
        from apps.reports.models import DeliveryStatus, ReportDeliveryLog
        from apps.reports.serializers import GeneratedReportLightSerializer

        smtp["error"] = Exception(SES_SANDBOX_ERROR)
        result = self._send(report)

        log = ReportDeliveryLog.objects.get()
        assert log.status == DeliveryStatus.PERMANENTLY_FAILED
        assert "not verified" in log.error_message
        assert result["sent"] == 0
        stats = GeneratedReportLightSerializer(report).data["delivery_stats"]
        assert stats == {"sent": 0, "failed": 1, "pending": 0}

    def test_delivered_report_email_uses_internal_sender(self, smtp, report):
        from apps.reports.models import DeliveryStatus, ReportDeliveryLog

        result = self._send(report)

        assert ReportDeliveryLog.objects.get().status == DeliveryStatus.SENT
        assert result["sent"] == 1
        assert smtp["profiles"] == ["internal"]
        assert len(mail.outbox) == 1


def test_worker_consumes_every_queue_used_by_tasks_and_beat():
    """Une file sans worker = des tâches qui ne s'exécutent jamais (rapport du lundi)."""
    from config.celery import app

    entrypoint = Path(settings.BASE_DIR) / "scripts" / "entrypoint.sh"
    match = re.search(r"worker .*-Q ([\w,]+)", entrypoint.read_text())
    worker_queues = set(match.group(1).split(","))

    app.loader.import_default_modules()
    used = {settings.CELERY_TASK_DEFAULT_QUEUE}
    used |= {route["queue"] for route in settings.CELERY_TASK_ROUTES.values()}
    used |= {
        entry.get("options", {}).get("queue")
        for entry in app.conf.beat_schedule.values()
    } - {None}
    used |= {t.queue for t in app.tasks.values() if getattr(t, "queue", None)}

    assert used <= worker_queues, f"Files sans worker : {sorted(used - worker_queues)}"
