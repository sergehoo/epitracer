"""Rapport hebdomadaire : génération → envoi automatique, relances, doublons, états bloqués.

Constat en production (16/11/2026, envoi automatique de 08h00 bien exécuté) :
  - emails : SMTP 535 (authentification refusée, puis IP mise en liste noire
    à force de relances manuelles) ;
  - SMS : 7 numéros saisis « 07… » transformés en +225 + 9 chiffres (0 retiré),
    3 SMS en attente fournisseur (crédit Orange épuisé) ;
  - « Envoyer » renvoyait à tous (60 journaux pour 20 destinataires) et
    expédiait pendant la requête web (timeout 30 s) ;
  - la relance automatique retentait aussi les erreurs définitives.
L'envoi réel (fournisseurs) est remplacé par un faux `enqueue_notification`.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.notifications.models import Channel, MessageType, Notification, NotificationStatus
from apps.notifications.services.dispatcher import SendResult
from apps.notifications.services.errors import ErrorCode
from apps.notifications.services.router import normalize_phone_number
from apps.reports.models import (
    AutomatedReportRecipient,
    AutomatedReportSchedule,
    DeliveryStatus,
    GeneratedReport,
    PreferredChannel,
    ReportDeliveryLog,
    ReportStatus,
    ReportType,
)
from apps.reports.serializers import GeneratedReportLightSerializer
from apps.reports.tasks import (
    dispatch_weekly_report,
    generate_weekly_report,
    retry_failed_weekly_reports,
    send_weekly_report_email,
)

pytestmark = pytest.mark.django_db


class FakeSend:
    """Faux `enqueue_notification` : « sent », « queued » ou (erreur, code)."""

    def __init__(self):
        self.outcome = "sent"
        self.calls: list[dict] = []

    def __call__(self, **kw):
        self.calls.append(kw)
        if isinstance(self.outcome, tuple):
            error, code = self.outcome
            return SendResult(ok=False, error=error, error_code=code)
        status = (
            NotificationStatus.SENT if self.outcome == "sent" else NotificationStatus.QUEUED
        )
        notif = Notification.objects.create(
            channel=kw["channel"], recipient=kw["recipient"], body="ok",
            provider="smtp" if kw["channel"] == "email" else "orange_ci",
            status=status, message_type=MessageType.ADMIN_NOTICE,
            sent_at=timezone.now() if status == NotificationStatus.SENT else None,
            dedup_key=kw.get("dedup_key", ""),
        )
        return SendResult(ok=True, notification_id=notif.id, provider=notif.provider)


@pytest.fixture
def fake_send(monkeypatch):
    fake = FakeSend()
    monkeypatch.setattr(
        "apps.notifications.services.dispatcher.enqueue_notification", fake,
    )
    return fake


@pytest.fixture
def recipients():
    AutomatedReportRecipient.objects.create(
        full_name="Directeur INHP", email="dg@inhp.ci", phone_number="+2250701020304",
        preferred_channel=PreferredChannel.BOTH, consent_date=date.today(),
    )
    AutomatedReportRecipient.objects.create(
        full_name="Point focal", email="pf@inhp.ci",
        preferred_channel=PreferredChannel.EMAIL, consent_date=date.today(),
    )
    AutomatedReportRecipient.objects.create(
        full_name="Inactif", email="old@inhp.ci", is_active=False,
        preferred_channel=PreferredChannel.EMAIL,
    )


@pytest.fixture
def schedule():
    return AutomatedReportSchedule.objects.create(name="Hebdo INHP", report_type=ReportType.WEEKLY)


def _report(**kw) -> GeneratedReport:
    midnight = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = midnight - timedelta(days=7)
    defaults = dict(
        report_type=ReportType.WEEKLY, period_start=start,
        period_end=start + timedelta(days=6, hours=23, minutes=59),
        status=ReportStatus.READY, summary_data={}, generated_at=timezone.now(),
    )
    defaults.update(kw)
    return GeneratedReport.objects.create(**defaults)


def _old_report() -> GeneratedReport:
    """Rapport hors fenêtre de rattrapage : seul le canal testé est envoyé."""
    return _report(generated_at=timezone.now() - timedelta(days=3))


def _summary(report):
    data = GeneratedReportLightSerializer(GeneratedReport.objects.get(pk=report.pk)).data
    return data["delivery_state"], data["delivery_stats"]


def test_monday_dispatch_generates_then_sends_to_active_recipients(
    fake_send, recipients, schedule,
):
    result = dispatch_weekly_report.apply().result

    report = GeneratedReport.objects.get()
    assert result["ok"] and result["report_id"] == report.pk
    assert report.status == ReportStatus.READY
    # 2 emails + 1 SMS ; le destinataire inactif n'est pas servi.
    assert sorted(c["channel"] for c in fake_send.calls) == ["email", "email", "sms"]
    assert ReportDeliveryLog.objects.filter(status=DeliveryStatus.SENT).count() == 3
    assert _summary(report) == (
        "sent", {"sent": 3, "failed": 0, "pending": 0, "on_hold": 0, "total": 3},
    )


def test_manual_generation_also_sends_automatically(fake_send, recipients):
    report_id = generate_weekly_report.apply().result

    assert ReportDeliveryLog.objects.filter(report_id=report_id).count() == 3
    assert len(fake_send.calls) == 3


def test_replaying_dispatch_or_send_never_duplicates(fake_send, recipients, schedule):
    dispatch_weekly_report.apply()
    dispatch_weekly_report.apply()
    report = GeneratedReport.objects.get()
    send_weekly_report_email.apply(args=[report.pk])
    retry_failed_weekly_reports.apply()  # rattrapage périodique

    assert len(fake_send.calls) == 3
    assert ReportDeliveryLog.objects.count() == 3


def test_ready_is_not_sent(fake_send):
    report = _report()
    assert _summary(report)[0] == "planned"


def test_permanent_error_is_not_retried_automatically(fake_send, recipients):
    fake_send.outcome = (
        "(535, b'5.7.8 Authentication failed.')", ErrorCode.PROVIDER_AUTH,
    )
    report = _old_report()
    send_weekly_report_email.apply(args=[report.pk])

    logs = ReportDeliveryLog.objects.all()
    assert {log.status for log in logs} == {DeliveryStatus.PERMANENTLY_FAILED}
    assert all(log.next_retry_at is None for log in logs)

    fake_send.calls.clear()
    retry_failed_weekly_reports.apply()
    assert fake_send.calls == []
    assert _summary(report)[0] == "failed"


def test_invalid_number_without_code_is_classified_permanent(fake_send, recipients):
    fake_send.outcome = ("Numéro CI invalide : attendu 10 chiffres après +225, reçu 9", "")
    report = _report()
    from apps.reports.tasks import send_weekly_report_sms

    send_weekly_report_sms.apply(args=[report.pk])

    assert ReportDeliveryLog.objects.get().status == DeliveryStatus.PERMANENTLY_FAILED


def test_temporary_error_is_retried_with_bounded_backoff(fake_send, recipients):
    fake_send.outcome = ("Connection timed out", "")
    report = _old_report()
    send_weekly_report_email.apply(args=[report.pk])
    log = ReportDeliveryLog.objects.filter(recipient__email="dg@inhp.ci").get()
    assert log.status == DeliveryStatus.FAILED
    assert log.next_retry_at > timezone.now()  # backoff : pas de relance immédiate

    fake_send.calls.clear()
    retry_failed_weekly_reports.apply()
    assert fake_send.calls == []  # pas encore dû

    for attempt in (1, 2, 3):
        ReportDeliveryLog.objects.update(next_retry_at=timezone.now() - timedelta(seconds=1))
        retry_failed_weekly_reports.apply()
        log.refresh_from_db()
        assert log.retry_count == attempt
    assert log.status == DeliveryStatus.PERMANENTLY_FAILED  # borné à 3 relances
    assert ReportDeliveryLog.objects.count() == 2  # relance = même journal

    ReportDeliveryLog.objects.update(next_retry_at=timezone.now() - timedelta(seconds=1))
    fake_send.calls.clear()
    retry_failed_weekly_reports.apply()
    assert fake_send.calls == []


def test_retry_succeeds_after_temporary_error(fake_send, recipients):
    fake_send.outcome = ("Connection timed out", "")
    report = _report()
    send_weekly_report_email.apply(args=[report.pk])
    fake_send.outcome = "sent"
    ReportDeliveryLog.objects.update(next_retry_at=timezone.now() - timedelta(seconds=1))

    retry_failed_weekly_reports.apply()

    assert set(ReportDeliveryLog.objects.values_list("status", flat=True)) == {
        DeliveryStatus.SENT,
    }
    assert _summary(report)[0] == "sent"


def test_retry_failed_button_only_relaunches_failures(client, superadmin, fake_send, recipients):
    report = _report()
    dg = AutomatedReportRecipient.objects.get(email="dg@inhp.ci")
    pf = AutomatedReportRecipient.objects.get(email="pf@inhp.ci")
    ok = ReportDeliveryLog.objects.create(
        report=report, recipient=dg, channel=Channel.EMAIL, status=DeliveryStatus.SENT,
    )
    pending = ReportDeliveryLog.objects.create(
        report=report, recipient=dg, channel=Channel.SMS, status=DeliveryStatus.QUEUED,
    )
    failed = ReportDeliveryLog.objects.create(
        report=report, recipient=pf, channel=Channel.EMAIL,
        status=DeliveryStatus.PERMANENTLY_FAILED, error_message="(535, auth)",
    )
    assert _summary(report)[0] == "sending"
    client.force_login(superadmin)

    resp = client.post(f"/api/v1/reports/weekly/{report.pk}/retry-failed/")

    assert resp.status_code == 202 and resp.json()["retrying"] == 1
    assert [c["recipient"] for c in fake_send.calls] == ["pf@inhp.ci"]
    failed.refresh_from_db()
    ok.refresh_from_db()
    pending.refresh_from_db()
    assert failed.status == DeliveryStatus.SENT and failed.retry_count == 1
    assert ok.status == DeliveryStatus.SENT and pending.status == DeliveryStatus.QUEUED
    assert ReportDeliveryLog.objects.count() == 3

    # Plus rien à relancer : aucun nouvel envoi.
    resp = client.post(f"/api/v1/reports/weekly/{report.pk}/retry-failed/")
    assert resp.json()["retrying"] == 0 and len(fake_send.calls) == 1


def test_legacy_duplicates_count_once_and_only_latest_is_retried(fake_send, recipients):
    report = _report()
    pf = AutomatedReportRecipient.objects.get(email="pf@inhp.ci")
    for _ in range(3):  # anciens clics « Envoyer »
        ReportDeliveryLog.objects.create(
            report=report, recipient=pf, channel=Channel.EMAIL,
            status=DeliveryStatus.FAILED, error_message="Connection timed out",
        )
    assert _summary(report)[1]["total"] == 1

    retry_failed_weekly_reports.apply(kwargs={"report_id": report.pk})
    assert len(fake_send.calls) == 1


def test_stuck_generation_and_lost_delivery_are_reconciled(fake_send, recipients):
    old = timezone.now() - timedelta(hours=2)
    stuck = _report(status=ReportStatus.GENERATING, generated_at=None)
    GeneratedReport.objects.filter(pk=stuck.pk).update(updated_at=old)
    report = _report(period_start=stuck.period_start - timedelta(days=7),
                     period_end=stuck.period_end - timedelta(days=7),
                     generated_at=old - timedelta(days=3))
    dg = AutomatedReportRecipient.objects.get(email="dg@inhp.ci")
    held = Notification.objects.create(
        channel=Channel.SMS, recipient="+2250701020304", body="x", provider="orange_ci",
        status=NotificationStatus.ON_HOLD, error_code=ErrorCode.QUOTA_EXHAUSTED,
        message_type=MessageType.ADMIN_NOTICE,
    )
    on_hold = ReportDeliveryLog.objects.create(
        report=report, recipient=dg, channel=Channel.SMS, status=DeliveryStatus.QUEUED,
        notification_id=held.pk,
    )
    lost = ReportDeliveryLog.objects.create(
        report=report, recipient=dg, channel=Channel.EMAIL, status=DeliveryStatus.QUEUED,
    )
    ReportDeliveryLog.objects.update(updated_at=old)

    result = retry_failed_weekly_reports.apply().result

    stuck.refresh_from_db()
    assert stuck.status == ReportStatus.FAILED and "bloquée" in stuck.error_message
    lost.refresh_from_db()
    on_hold.refresh_from_db()
    # Envoi perdu avant sa mise en file : échec temporaire, relancé avec backoff.
    assert lost.status == DeliveryStatus.FAILED and lost.next_retry_at is not None
    # Crédit SMS épuisé : reste en attente fournisseur, jamais relancé en double.
    assert on_hold.status == DeliveryStatus.QUEUED
    assert fake_send.calls == []
    assert result["reconciled"] == 2
    state, stats = _summary(report)
    assert stats["on_hold"] == 1 and state == "sending"


def test_local_ivorian_number_keeps_its_leading_zero():
    assert normalize_phone_number("0709620252") == "+2250709620252"
    assert normalize_phone_number("07 09 62 02 52") == "+2250709620252"
    assert normalize_phone_number("+2250709620252") == "+2250709620252"
