"""Fiabilité du module Notifications.

Couvre les incidents observés en production (historique /notifications) :
  - rappels quotidiens envoyés deux fois (08:00 + 08:05), relances « Donnez-nous
    de vos nouvelles » toutes les 6 h, suivis multimaladies ;
  - Orange CI HTTP 403 / POL0001 (crédit épuisé) retenté 3 fois, réponse brute
    affichée aux agents ;
  - absence de reprise contrôlée après réapprovisionnement.

Les fournisseurs (Orange CI, Twilio) sont mockés : aucun appel réseau.
"""

from __future__ import annotations

import threading
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from django.db import connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, RoleAssignment, RoleCode
from apps.companion import tasks as companion_tasks
from apps.companion.models import ConsentScope
from apps.companion.services import record_consent
from apps.notifications.models import (
    Channel,
    MessageType,
    Notification,
    NotificationAuditAction,
    NotificationAuditLog,
    NotificationStatus,
    Provider,
    ProviderAvailability,
    ProviderState,
    ReminderDispatch,
)
from apps.notifications.services import availability
from apps.notifications.services.dispatcher import enqueue_notification
from apps.notifications.services.errors import ErrorCode, classify_error, friendly_error
from apps.notifications.services.idempotence import (
    ReminderKind,
    claim_reminder,
    reminder_dedup_key,
)
from apps.notifications.services.sms_orange_ci import OrangeSendResult
from apps.notifications.services.sms_twilio import TwilioSendResult

CI_PHONE = "+2250708090911"
INTL_PHONE = "+33612345678"
ORANGE_QUOTA_BODY = (
    '{"requestError":{"policyException":{"messageId":"POL0001",'
    '"text":"A policy error occurred. For example, rate of messages authorized '
    'exceeded. %1","variables":["You consumed all available units. You can buy '
    'a new bundle on https://developer.orange.com"]}}}'
)
ORANGE_QUOTA_ERROR = f"Orange CI HTTP 403 : {ORANGE_QUOTA_BODY}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def orange(monkeypatch):
    """Client Orange CI mocké — succès par défaut, configurable par test."""
    mock = MagicMock(return_value=OrangeSendResult(ok=True, provider_message_id="orange-1"))
    monkeypatch.setattr("apps.notifications.services.sms_orange_ci.send_sms", mock)
    return mock


@pytest.fixture
def orange_quota(orange):
    orange.return_value = OrangeSendResult(
        ok=False,
        error=ORANGE_QUOTA_ERROR,
        error_code=ErrorCode.QUOTA_EXHAUSTED,
    )
    return orange


@pytest.fixture
def twilio(monkeypatch):
    mock = MagicMock(return_value=TwilioSendResult(ok=True, provider_message_id="SM1"))
    monkeypatch.setattr("apps.notifications.services.sms_twilio.send_sms", mock)
    return mock


@pytest.fixture
def district_agent(db, django_user_model, roles):
    user = django_user_model.objects.create_user(
        email="agent@example.ci",
        username="agent@example.ci",
        password="StrongPwd!2026",
    )
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(code=RoleCode.DISTRICT),
        is_active=True,
    )
    return user


@pytest.fixture
def second_disease(db):
    from apps.diseases.models import Disease, DiseaseSeverity

    return Disease.objects.create(
        code="MPOX",
        name="Mpox",
        short_name="Mpox",
        severity=DiseaseSeverity.HIGH,
        color="#7c3aed",
        incubation_min_days=5,
        incubation_max_days=21,
        surveillance_days=21,
        quarantine_days=21,
        risk_countries=["CD"],
        requires_quarantine=True,
        requires_pass=True,
    )


def _followup(traveler, disease, *, started_days_ago=5, ends_in_days=16):
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    today = date.today()
    return QuarantineRecord.objects.create(
        traveler=traveler,
        disease=disease,
        started_on=today - timedelta(days=started_days_ago),
        expected_end_on=today + timedelta(days=ends_in_days),
        status=QuarantineStatus.ACTIVE,
        address="Cocody",
    )


@pytest.fixture
def multi_followup_traveler(traveler, ebola_disease, second_disease):
    """Voyageur suivi pour 2 maladies, consentant, sans appareil push actif
    (→ repli SMS Orange CI)."""
    _followup(traveler, ebola_disease)
    _followup(traveler, second_disease, ends_in_days=10)
    record_consent(
        traveler=traveler,
        scope=ConsentScope.PUSH_NOTIFICATIONS,
        granted=True,
        version="v1.0",
    )
    return traveler


def _consent(traveler):
    record_consent(
        traveler=traveler,
        scope=ConsentScope.PUSH_NOTIFICATIONS,
        granted=True,
        version="v1.0",
    )


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


def _notif(**kw) -> Notification:
    """Ligne d'historique créée directement (sans déclencher d'envoi)."""
    defaults = dict(
        channel=Channel.SMS,
        recipient=CI_PHONE,
        normalized_phone=CI_PHONE,
        body="Bonjour",
        provider=Provider.ORANGE_CI,
        status=NotificationStatus.QUEUED,
        message_type=MessageType.MANUAL_MESSAGE,
    )
    defaults.update(kw)
    return Notification.objects.create(**defaults)


def _suspend_orange():
    ProviderAvailability.objects.update_or_create(
        provider=Provider.ORANGE_CI,
        defaults={
            "state": ProviderState.QUOTA_EXHAUSTED,
            "reason_code": ErrorCode.QUOTA_EXHAUSTED,
            "technical_detail": ORANGE_QUOTA_ERROR,
            "suspended_at": timezone.now(),
        },
    )


# ===========================================================================
# 1. Idempotence en base
# ===========================================================================
@pytest.mark.django_db
class TestIdempotence:
    def test_claim_once_per_traveler_kind_and_date(self, traveler):
        today = date.today()
        assert claim_reminder(traveler, ReminderKind.DAILY_CHECKIN, today) is True
        assert claim_reminder(traveler, ReminderKind.DAILY_CHECKIN, today) is False
        assert claim_reminder(traveler, ReminderKind.DAILY_CHECKIN, today) is False
        # Autre type ou autre jour : nouveau rappel autorisé.
        assert claim_reminder(traveler, ReminderKind.MISSED_CHECKIN, today) is True
        tomorrow = today + timedelta(days=1)
        assert claim_reminder(traveler, ReminderKind.DAILY_CHECKIN, tomorrow) is True

        row = ReminderDispatch.objects.get(
            traveler=traveler,
            kind=ReminderKind.DAILY_CHECKIN,
            reminder_date=today,
        )
        assert row.duplicates_avoided == 2

    def test_same_dedup_key_creates_a_single_notification(self, traveler, orange):
        key = reminder_dedup_key(ReminderKind.DAILY_CHECKIN, traveler.pk, date.today(), "sms")
        kwargs = dict(
            channel="sms",
            recipient=CI_PHONE,
            body="Rappel",
            traveler=traveler,
            dedup_key=key,
        )
        first = enqueue_notification(**kwargs)
        second = enqueue_notification(**kwargs)

        assert first.ok and not first.duplicate
        assert second.ok and second.duplicate
        assert second.notification_id == first.notification_id
        assert Notification.objects.filter(dedup_key=key).count() == 1
        assert orange.call_count == 1
        duplicates = NotificationAuditLog.objects.filter(action=NotificationAuditAction.DUPLICATE)
        assert duplicates.count() == 1

    def test_urgent_and_manual_messages_are_never_deduplicated(self, traveler, orange):
        for _ in range(2):
            enqueue_notification(
                channel="sms",
                recipient=CI_PHONE,
                body="Symptôme critique déclaré",
                traveler=traveler,
                message_type=MessageType.SYMPTOM_ALERT,
            )
            enqueue_notification(
                channel="sms",
                recipient=CI_PHONE,
                body="Merci de rappeler l'INHP",
                traveler=traveler,
                message_type=MessageType.MANUAL_MESSAGE,
            )
        assert Notification.objects.filter(message_type=MessageType.SYMPTOM_ALERT).count() == 2
        assert Notification.objects.filter(message_type=MessageType.MANUAL_MESSAGE).count() == 2

    def test_daily_reminder_once_despite_multi_followups_and_repeated_jobs(
        self,
        multi_followup_traveler,
        orange,
    ):
        from apps.medical.tasks import send_daily_followup_reminders as medical_daily

        # 08:00 companion, 08:05 médical (déléguait auparavant à companion),
        # alias historique encore planifié, retry Celery de la tâche.
        companion_tasks.send_daily_checkin_reminders.run()
        medical_daily.run()
        companion_tasks.send_daily_followup_reminders.run()
        companion_tasks.send_daily_checkin_reminders.run()

        sms = Notification.objects.filter(
            traveler=multi_followup_traveler,
            channel=Channel.SMS,
            message_type=MessageType.FOLLOWUP_REMINDER,
        )
        assert sms.count() == 1
        assert sms.get().status == NotificationStatus.SENT
        assert orange.call_count == 1
        dispatch = ReminderDispatch.objects.get(
            traveler=multi_followup_traveler,
            kind=ReminderKind.DAILY_CHECKIN,
        )
        assert dispatch.duplicates_avoided == 2

    def test_missed_checkin_relance_at_most_once_a_day(self, multi_followup_traveler, orange):
        from apps.quarantine.models import QuarantineRecord

        # Suivis ouverts il y a 3 jours, aucun check-in depuis.
        QuarantineRecord.objects.filter(traveler=multi_followup_traveler).update(
            created_at=timezone.now() - timedelta(days=3),
        )
        for _ in range(3):  # 06:15, 12:15, 18:15
            companion_tasks.detect_missed_checkins.run()

        relances = Notification.objects.filter(
            traveler=multi_followup_traveler,
            body__startswith="Donnez-nous de vos nouvelles",
        )
        assert relances.count() == 1
        assert orange.call_count == 1
        assert (
            ReminderDispatch.objects.get(
                traveler=multi_followup_traveler,
                kind=ReminderKind.MISSED_CHECKIN,
            ).duplicates_avoided
            == 2
        )

    def test_completion_message_sent_once_when_last_followup_ends(
        self,
        traveler,
        ebola_disease,
        second_disease,
        orange,
    ):
        _consent(traveler)
        _followup(traveler, ebola_disease, started_days_ago=21, ends_in_days=0)
        _followup(traveler, second_disease, started_days_ago=21, ends_in_days=0)

        stats = companion_tasks.send_completion_messages.run()

        assert stats["completed"] == 2
        assert (
            Notification.objects.filter(
                traveler=traveler,
                message_type=MessageType.FOLLOWUP_COMPLETED,
            ).count()
            == 1
        )
        assert stats["duplicates_avoided"] == 1

    def test_completion_message_deferred_while_another_followup_continues(
        self,
        traveler,
        ebola_disease,
        second_disease,
        orange,
    ):
        _consent(traveler)
        _followup(traveler, ebola_disease, started_days_ago=21, ends_in_days=0)
        _followup(traveler, second_disease, started_days_ago=5, ends_in_days=16)

        stats = companion_tasks.send_completion_messages.run()

        assert stats["deferred_other_followups"] == 1
        assert not Notification.objects.filter(message_type=MessageType.FOLLOWUP_COMPLETED).exists()

    def test_unrendered_template_variable_is_refused(self, traveler, orange):
        res = enqueue_notification(channel="sms", recipient=CI_PHONE, body="ID : {traveler_id}.")
        assert not res.ok
        assert "{traveler_id}" in res.error
        assert not Notification.objects.exists()

        ok = enqueue_notification(
            channel="sms",
            recipient=CI_PHONE,
            body="ID : {traveler_id}.",
            traveler=traveler,
        )
        assert ok.ok
        assert Notification.objects.get().body == f"ID : {traveler.public_id}."


# ===========================================================================
# 2. Concurrence (vraies transactions PostgreSQL, une connexion par thread)
# ===========================================================================
@pytest.fixture
def live_db(django_db_setup, django_db_blocker):
    """Base de test en autocommit : chaque thread a sa propre connexion et voit
    les écritures validées des autres, comme des workers Celery concurrents.

    Pas de `django_db(transaction=True)` : son flush final effacerait les
    données de référence semées par les migrations (le projet tourne en
    `--reuse-db`). Chaque test supprime donc lui-même ce qu'il a créé.
    """
    with django_db_blocker.unblock():
        yield


def _run_threads(n: int, target) -> list:
    barrier = threading.Barrier(n)
    results: list = [None] * n
    errors: list = []

    def worker(i):
        try:
            barrier.wait(timeout=10)
            results[i] = target()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors, errors
    return results


class TestConcurrency:
    def test_concurrent_enqueue_with_same_key_keeps_one_row(self, live_db, monkeypatch):
        monkeypatch.setattr(
            "apps.notifications.tasks.send_notification_task.delay",
            lambda *a, **k: None,
        )
        key = f"daily_checkin:test-concurrency:{timezone.now():%Y%m%d%H%M%S%f}:sms"
        try:
            results = _run_threads(
                6,
                lambda: enqueue_notification(
                    channel="sms",
                    recipient=CI_PHONE,
                    body="Rappel du jour",
                    dedup_key=key,
                ),
            )
            assert Notification.objects.filter(dedup_key=key).count() == 1
            assert sum(1 for r in results if r.ok and not r.duplicate) == 1
            assert sum(1 for r in results if r.duplicate) == 5
        finally:
            Notification.all_objects.filter(dedup_key=key).delete()

    def test_concurrent_claims_have_a_single_winner(self, live_db):
        from apps.travelers.models import Traveler

        traveler = Traveler.objects.create(
            first_name="Test",
            last_name="CONCURRENCE",
            gender="F",
            id_document_number="CONC-1",
            phone_mobile=CI_PHONE,
        )
        try:
            results = _run_threads(6, lambda: claim_reminder(traveler, ReminderKind.DAILY_CHECKIN))
            assert results.count(True) == 1
            assert ReminderDispatch.objects.get(traveler=traveler).duplicates_avoided == 5
        finally:
            ReminderDispatch.all_objects.filter(traveler_id=traveler.pk).delete()
            Traveler.all_objects.filter(pk=traveler.pk).delete()
            Traveler.history.filter(id=traveler.pk).delete()

    def test_send_task_skips_a_notification_locked_by_another_worker(self, live_db, orange):
        from apps.notifications.tasks import send_notification_task

        notif = _notif()
        locked, release = threading.Event(), threading.Event()

        def other_worker():
            try:
                with transaction.atomic():
                    Notification.objects.select_for_update().get(pk=notif.pk)
                    locked.set()
                    release.wait(10)
            finally:
                connection.close()

        t = threading.Thread(target=other_worker)
        try:
            t.start()
            assert locked.wait(10)
            try:
                res = send_notification_task.run(notif.pk)
                assert res == {"ok": True, "skipped": True, "status": "locked"}
                assert orange.call_count == 0
            finally:
                release.set()
                t.join(10)

            send_notification_task.run(notif.pk)
            send_notification_task.run(notif.pk)  # redélivrance : déjà SENT → ignorée
            notif.refresh_from_db()
            assert notif.status == NotificationStatus.SENT
            assert orange.call_count == 1
        finally:
            Notification.all_objects.filter(pk=notif.pk).delete()


# ===========================================================================
# 3. Orange CI : crédit épuisé (403 / POL0001)
# ===========================================================================
@pytest.mark.django_db
class TestOrangeQuota:
    def test_http_403_pol0001_is_classified_as_quota_exhausted(self, settings, monkeypatch):
        from apps.notifications.services import sms_orange_ci

        settings.NOTIFICATIONS = {
            **settings.NOTIFICATIONS,
            "ORANGE_CI_SMS_ENABLED": True,
            "ORANGE_CI_SMS_CLIENT_ID": "id",
            "ORANGE_CI_SMS_CLIENT_SECRET": "secret",
            "ORANGE_CI_SMS_SENDER_MSISDN": "+2250709862860",
        }
        monkeypatch.setattr(sms_orange_ci, "_get_access_token", lambda force_refresh=False: "tok")
        response = MagicMock(status_code=403, text=ORANGE_QUOTA_BODY, headers={})
        monkeypatch.setattr(sms_orange_ci.httpx, "post", MagicMock(return_value=response))

        res = sms_orange_ci.send_sms(CI_PHONE, "Bonjour")

        assert not res.ok
        assert res.error_code == ErrorCode.QUOTA_EXHAUSTED
        # Texte tronqué tel qu'affiché dans l'historique avant correctif.
        assert classify_error(ORANGE_QUOTA_ERROR[:200]) == ErrorCode.QUOTA_EXHAUSTED
        assert "POL0001" not in friendly_error(ErrorCode.QUOTA_EXHAUSTED)

    def test_quota_exhausted_holds_suspends_and_alerts_admins_once(
        self,
        superadmin,
        orange_quota,
        twilio,
        django_capture_on_commit_callbacks,
    ):
        with django_capture_on_commit_callbacks(execute=True):
            first = enqueue_notification(channel="sms", recipient=CI_PHONE, body="Rappel 1")

        notif = Notification.objects.get(pk=first.notification_id)
        assert notif.status == NotificationStatus.ON_HOLD
        assert notif.error_code == ErrorCode.QUOTA_EXHAUSTED
        assert notif.retry_count == 1  # aucune relance automatique
        state = ProviderAvailability.objects.get(provider=Provider.ORANGE_CI)
        assert state.state == ProviderState.QUOTA_EXHAUSTED
        alerts = Notification.objects.filter(message_type=MessageType.ADMIN_NOTICE)
        assert list(alerts.values_list("recipient", flat=True)) == [superadmin.email]

        # Pendant la suspension : plus aucun appel Orange, aucune bascule Twilio.
        with django_capture_on_commit_callbacks(execute=True):
            for i in range(2):
                enqueue_notification(channel="sms", recipient=CI_PHONE, body=f"Rappel {i + 2}")

        held = Notification.objects.filter(channel=Channel.SMS, status=NotificationStatus.ON_HOLD)
        assert held.count() == 3
        assert set(held.values_list("provider", flat=True)) == {Provider.ORANGE_CI}
        assert orange_quota.call_count == 1
        assert twilio.call_count == 0
        assert alerts.count() == 1  # une seule alerte par incident
        state.refresh_from_db()
        assert state.blocked_attempts == 2

    def test_ci_number_never_falls_back_to_twilio(self, twilio):
        from apps.notifications.tasks import send_notification_task

        notif = _notif(provider=Provider.TWILIO)  # routage legacy / erroné
        res = send_notification_task.run(notif.pk)

        notif.refresh_from_db()
        assert res["ok"] is False
        assert notif.status == NotificationStatus.FAILED
        assert notif.error_code == ErrorCode.NATIONAL_POLICY
        assert twilio.call_count == 0

    def test_forced_twilio_for_ci_number_is_refused(self):
        res = enqueue_notification(
            channel="sms",
            recipient=CI_PHONE,
            body="Test",
            force_provider=Provider.TWILIO,
        )
        assert not res.ok and "politique nationale" in res.error

    def test_international_numbers_still_use_twilio_during_orange_suspension(self, orange, twilio):
        _suspend_orange()
        res = enqueue_notification(channel="sms", recipient=INTL_PHONE, body="Hello")
        assert Notification.objects.get(pk=res.notification_id).status == NotificationStatus.SENT
        assert twilio.call_count == 1 and orange.call_count == 0

    def test_urgent_alert_is_still_attempted_while_suspended(self, orange):
        _suspend_orange()
        res = enqueue_notification(
            channel="sms",
            recipient=CI_PHONE,
            body="Alerte symptôme critique",
            message_type=MessageType.SYMPTOM_ALERT,
        )
        assert Notification.objects.get(pk=res.notification_id).status == NotificationStatus.SENT
        assert orange.call_count == 1

    def test_periodic_retry_skips_definitive_errors_and_suspended_provider(self, monkeypatch):
        from apps.notifications import tasks

        delay = MagicMock()
        monkeypatch.setattr(tasks.send_notification_task, "delay", delay)
        now = timezone.now()
        _notif(
            status=NotificationStatus.FAILED,
            failed_at=now,
            retry_count=1,
            error_code=ErrorCode.QUOTA_EXHAUSTED,
            error_message=ORANGE_QUOTA_ERROR,
        )
        _notif(
            status=NotificationStatus.FAILED,
            failed_at=now,
            retry_count=1,
            error_code=ErrorCode.INVALID_NUMBER,
        )
        retryable = _notif(
            status=NotificationStatus.FAILED,
            failed_at=now,
            retry_count=1,
            provider=Provider.TWILIO,
            recipient=INTL_PHONE,
            normalized_phone=INTL_PHONE,
            error_code=ErrorCode.NETWORK,
        )
        _suspend_orange()
        _notif(
            status=NotificationStatus.FAILED,
            failed_at=now,
            retry_count=1,
            error_code=ErrorCode.NETWORK,
        )

        assert tasks.retry_failed_notifications() == {"requeued": 1}
        delay.assert_called_once_with(retryable.id)


# ===========================================================================
# 4. Reprise contrôlée après réapprovisionnement
# ===========================================================================
@pytest.mark.django_db
class TestResume:
    URL = "/api/v1/notifications/providers/orange_ci/resume/"

    def test_resume_requeues_relevant_messages_and_expires_stale_reminders(
        self,
        superadmin,
        traveler,
        orange,
        django_capture_on_commit_callbacks,
    ):
        _suspend_orange()
        manual = _notif(
            status=NotificationStatus.ON_HOLD,
            error_code=ErrorCode.QUOTA_EXHAUSTED,
            retry_count=1,
        )
        yesterday = date.today() - timedelta(days=1)
        stale = _notif(
            status=NotificationStatus.ON_HOLD,
            error_code=ErrorCode.PROVIDER_SUSPENDED,
            traveler=traveler,
            message_type=MessageType.FOLLOWUP_REMINDER,
            body="Jour 20/21 de surveillance",
            dedup_key=reminder_dedup_key(ReminderKind.DAILY_CHECKIN, traveler.pk, yesterday, "sms"),
            metadata={"reminder_date": yesterday.isoformat()},
        )

        with django_capture_on_commit_callbacks(execute=True):
            resp = _client(superadmin).post(self.URL, {"requeue": True}, format="json")

        assert resp.status_code == 200, resp.data
        assert resp.data == {
            "provider": "orange_ci",
            "was_suspended": True,
            "requeued": 1,
            "expired": 1,
        }
        manual.refresh_from_db()
        stale.refresh_from_db()
        assert manual.status == NotificationStatus.SENT
        assert stale.status == NotificationStatus.CANCELLED
        assert stale.error_code == ErrorCode.EXPIRED_ON_HOLD
        assert orange.call_count == 1
        state = ProviderAvailability.objects.get(provider=Provider.ORANGE_CI)
        assert state.state == ProviderState.AVAILABLE
        assert state.resumed_by == superadmin
        assert state.history.count() >= 2  # suspension + reprise tracées

    def test_resume_is_reserved_to_admin_roles(self, district_agent):
        _suspend_orange()
        resp = _client(district_agent).post(self.URL, {}, format="json")
        assert resp.status_code == 403
        assert availability.is_suspended(Provider.ORANGE_CI)

    def test_manual_retry_refused_while_provider_suspended(self, superadmin):
        _suspend_orange()
        notif = _notif(status=NotificationStatus.FAILED, error_code=ErrorCode.QUOTA_EXHAUSTED)
        resp = _client(superadmin).post(f"/api/v1/notifications/{notif.pk}/retry/")
        assert resp.status_code == 409
        notif.refresh_from_db()
        assert notif.status == NotificationStatus.FAILED


# ===========================================================================
# 5. API : erreurs lisibles, indicateurs, filtres
# ===========================================================================
@pytest.mark.django_db
class TestNotificationsApi:
    def test_agents_never_see_raw_provider_responses(self, district_agent, superadmin):
        _notif(
            status=NotificationStatus.ON_HOLD,
            error_code=ErrorCode.QUOTA_EXHAUSTED,
            error_message=ORANGE_QUOTA_ERROR,
        )
        # Ligne historique sans error_code (antérieure au correctif).
        _notif(status=NotificationStatus.FAILED, error_message=ORANGE_QUOTA_ERROR)

        agent_rows = _client(district_agent).get("/api/v1/notifications/").data["results"]
        assert len(agent_rows) == 2
        for row in agent_rows:
            assert "POL0001" not in row["error_message"]
            assert row["error_message"] == friendly_error(ErrorCode.QUOTA_EXHAUSTED)
            assert row["technical_error"] is None

        admin_rows = _client(superadmin).get("/api/v1/notifications/").data["results"]
        assert all("POL0001" in row["technical_error"] for row in admin_rows)

        providers = _client(district_agent).get("/api/v1/notifications/providers/").data["results"]
        assert {p["provider"] for p in providers} == {"orange_ci", "twilio"}
        assert all(p["is_suspended"] is False for p in providers)

    def test_stats_and_filters(self, district_agent, traveler, ebola_disease):
        _followup(traveler, ebola_disease)
        _notif(status=NotificationStatus.SENT, body="x" * 170, traveler=traveler)  # 2 SMS
        _notif(
            status=NotificationStatus.DELIVERED,
            provider=Provider.TWILIO,
            recipient=INTL_PHONE,
            normalized_phone=INTL_PHONE,
        )
        _notif(status=NotificationStatus.FAILED, error_code=ErrorCode.NETWORK)
        _notif(status=NotificationStatus.ON_HOLD, error_code=ErrorCode.QUOTA_EXHAUSTED)
        _notif(status=NotificationStatus.QUEUED)
        _notif(
            channel=Channel.EMAIL,
            provider=Provider.SMTP,
            recipient="a@b.ci",
            normalized_phone="",
            status=NotificationStatus.SENT,
        )
        ReminderDispatch.objects.create(
            traveler=traveler,
            kind=ReminderKind.DAILY_CHECKIN,
            reminder_date=date.today(),
            duplicates_avoided=2,
        )
        NotificationAuditLog.objects.create(
            notification=Notification.objects.first(),
            action=NotificationAuditAction.DUPLICATE,
        )

        client = _client(district_agent)
        stats = client.get("/api/v1/notifications/stats/").data
        assert stats["total"] == 6
        assert stats["sent"] == 3
        assert stats["failed"] == 1
        assert stats["pending"] == 2 and stats["on_hold"] == 1
        assert stats["duplicates_avoided"] == 3
        assert stats["sms"]["messages"] == 2
        assert stats["sms"]["segments"] == 3
        assert {r["provider"]: r["segments"] for r in stats["sms"]["by_provider"]} == {
            "orange_ci": 2,
            "twilio": 1,
        }

        def count(**params):
            return client.get("/api/v1/notifications/", params).data["count"]

        assert count(status="on_hold") == 1
        assert count(status="waiting") == 2
        assert count(status="sent_all", channel="sms") == 2
        assert count(provider="twilio") == 1
        assert count(channel="email") == 1
        assert count(disease="EBOLA") == 1
        assert count(search="DIALLO") == 1
        assert count(date_from=(date.today() + timedelta(days=1)).isoformat()) == 0
        assert client.get("/api/v1/notifications/stats/", {"disease": "EBOLA"}).data["total"] == 1
