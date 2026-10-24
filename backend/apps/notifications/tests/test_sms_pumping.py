"""Protection contre le SMS pumping et l'épuisement frauduleux des crédits.

Scénarios : spam OTP (multi-IP), rejeu (OTP, Turnstile, requête), inscriptions
massives, appels concurrents, échec fournisseur, dépassement de budget,
plafond des urgences, pics internationaux, RBAC des envois agents et routage
strict Orange CI (+225) / Twilio (international).

Les fournisseurs et Cloudflare sont mockés : aucun appel réseau.
"""

from __future__ import annotations

import re
import threading
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from django.core.cache import cache
from django.db import connection
from rest_framework.test import APIClient

from apps.accounts.models import Role, RoleAssignment, RoleCode
from apps.mobile_api.voyageur_auth import VoyageurRequestOtpView, VoyageurVerifyOtpView
from apps.notifications.models import (
    Channel,
    MessageType,
    Notification,
    NotificationStatus,
    Provider,
    ProviderAvailability,
    ProviderState,
    SmsSecurityEvent,
)
from apps.notifications.services.dispatcher import enqueue_notification
from apps.notifications.services.errors import ErrorCode
from apps.notifications.services.security import SecurityEventKind
from apps.notifications.services.sms_orange_ci import OrangeSendResult
from apps.notifications.services.sms_twilio import TwilioSendResult

CI_PHONE = "+2250708090911"  # numéro de la fixture `traveler`
OTP_URL = "/api/mobile/auth/voyageur/request-otp/"
VERIFY_URL = "/api/mobile/auth/voyageur/verify-otp/"
REGISTER_URL = "/api/v1/ebola/public/register/"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def orange(monkeypatch):
    mock = MagicMock(return_value=OrangeSendResult(ok=True, provider_message_id="orange-1"))
    monkeypatch.setattr("apps.notifications.services.sms_orange_ci.send_sms", mock)
    return mock


@pytest.fixture
def twilio(monkeypatch):
    mock = MagicMock(return_value=TwilioSendResult(ok=True, provider_message_id="SM1"))
    monkeypatch.setattr("apps.notifications.services.sms_twilio.send_sms", mock)
    return mock


@pytest.fixture(autouse=True)
def admin_mailbox(monkeypatch):
    """Emails d'alerte administrateur : capturés, sans connexion SMTP."""
    from apps.notifications.providers import SendResult

    mock = MagicMock(return_value=SendResult(ok=True, provider="smtp", provider_id="test"))
    monkeypatch.setattr("apps.notifications.providers.send_email", mock)
    return mock


@pytest.fixture
def guard(settings):
    """Garde SMS avec des limites réduites, modifiables par test."""
    cfg = {
        **settings.SMS_GUARD,
        "PER_NUMBER": {"otp": (3, 6), "standard": (6, 12), "urgent": (10, 30)},
        "PER_PROVIDER_DAY": {"orange_ci": 1000, "twilio": 1000},
        "BUDGET_DAILY": 1000,
        "BUDGET_MONTHLY": 10000,
        "URGENT_DAILY": 100,
        "SPIKE_INTL_PREFIX_HOUR": 0,
        "SPIKE_INTL_TOTAL_HOUR": 0,
        "ALLOWED_CALLING_CODES": [],
    }
    settings.SMS_GUARD = cfg
    return cfg


@pytest.fixture
def no_drf_throttle(monkeypatch):
    """Isole la couche applicative (les throttles DRF par IP sont testés ailleurs)."""
    monkeypatch.setattr(VoyageurRequestOtpView, "throttle_classes", [])
    monkeypatch.setattr(VoyageurVerifyOtpView, "throttle_classes", [])


@pytest.fixture
def turnstile_on(settings, monkeypatch):
    settings.TURNSTILE = {**settings.TURNSTILE, "SECRET_KEY": "test-secret"}
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(data["response"])
        ok = data["response"].startswith("good")
        payload = {
            "success": ok,
            "action": "otp_request" if "otp" in data["response"] else "public_registration",
        }
        if not ok:
            payload["error-codes"] = ["invalid-input-response"]
        return MagicMock(json=MagicMock(return_value=payload))

    monkeypatch.setattr("apps.core.turnstile.httpx.post", fake_post)
    return calls


def _user(django_user_model, email, role):
    user = django_user_model.objects.create_user(
        email=email, username=email, password="StrongPwd!2026"
    )
    RoleAssignment.objects.create(user=user, role=Role.objects.get(code=role), is_active=True)
    return user


@pytest.fixture
def district_agent(db, django_user_model, roles):
    return _user(django_user_model, "district@example.ci", RoleCode.DISTRICT)


def _client(user=None, ip="10.0.0.1") -> APIClient:
    c = APIClient(REMOTE_ADDR=ip)
    if user is not None:
        c.force_authenticate(user)
    return c


def _sms(**kw):
    defaults = dict(channel="sms", body="Rappel EpiTrace")
    defaults.update(kw)
    return enqueue_notification(**defaults)


def _events(kind):
    return SmsSecurityEvent.objects.filter(kind=kind)


def _otp_sms():
    return Notification.objects.filter(message_type=MessageType.OTP)


# ===========================================================================
# 1. OTP : spam, rejeu, énumération
# ===========================================================================
@pytest.mark.django_db
class TestOtpSpam:
    def test_spam_on_one_number_is_capped_even_when_rotating_ips(
        self,
        traveler,
        orange,
        guard,
        no_drf_throttle,
    ):
        for i in range(12):
            cache.delete(f"voyageur_otp_cooldown:{traveler.pk}")
            resp = _client(ip=f"10.1.0.{i}").post(OTP_URL, {"phone": CI_PHONE}, format="json")
            assert resp.status_code == 200
            assert resp.data["message"].startswith("Si vous êtes enregistré")

        assert _otp_sms().count() == 3  # RL_OTP_PHONE : 3 / 10 min
        assert orange.call_count == 3
        assert _events(SecurityEventKind.RATE_LIMITED).filter(source="otp_request").exists()

    def test_otp_goes_only_to_the_registered_number(self, traveler, orange, guard, no_drf_throttle):
        resp = _client().post(
            OTP_URL, {"passport_number": "P123456", "phone": "+33699999999"}, format="json"
        )
        assert resp.status_code == 200
        sms = _otp_sms().get()
        assert sms.normalized_phone == CI_PHONE
        assert sms.provider == Provider.ORANGE_CI

    def test_repeated_request_within_cooldown_sends_a_single_code(
        self, traveler, orange, no_drf_throttle
    ):
        for _ in range(3):
            _client().post(OTP_URL, {"phone": CI_PHONE}, format="json")
        assert _otp_sms().count() == 1

    def test_unknown_traveler_gets_the_same_neutral_answer_and_no_sms(
        self, traveler, orange, no_drf_throttle
    ):
        known = _client(ip="10.2.0.1").post(OTP_URL, {"phone": CI_PHONE}, format="json")
        unknown = _client(ip="10.2.0.2").post(OTP_URL, {"phone": "+2250102030405"}, format="json")
        assert known.status_code == unknown.status_code == 200
        assert set(known.data) == set(unknown.data)
        assert known.data["message"] == unknown.data["message"]
        assert _otp_sms().count() == 1

    def test_ip_rate_limit(self, traveler, orange, no_drf_throttle):
        codes = [
            _client(ip="10.3.0.1")
            .post(OTP_URL, {"phone": f"+22501020304{i:02d}"}, format="json")
            .status_code
            for i in range(6)
        ]
        assert codes == [200] * 5 + [429]

    def test_verify_replay_is_rejected_and_logged(self, traveler, orange, no_drf_throttle):
        _client().post(OTP_URL, {"phone": CI_PHONE}, format="json")
        code = re.search(r"\b(\d{6})\b", _otp_sms().get().body).group(1)

        first = _client().post(VERIFY_URL, {"phone": CI_PHONE, "code": code}, format="json")
        replay = _client().post(VERIFY_URL, {"phone": CI_PHONE, "code": code}, format="json")

        assert first.status_code == 200 and "access" in first.data
        assert replay.status_code == 410
        assert _events(SecurityEventKind.OTP_REPLAY).count() == 1

    def test_otp_code_never_shown_in_history(self, traveler, orange, superadmin, no_drf_throttle):
        _client().post(OTP_URL, {"phone": CI_PHONE}, format="json")
        rows = _client(superadmin).get("/api/v1/notifications/").data["results"]
        otp_rows = [r for r in rows if r["message_type"] == "otp"]
        assert otp_rows and not re.search(r"\d{6}", otp_rows[0]["body"])


# ===========================================================================
# 2. Turnstile vérifié côté serveur
# ===========================================================================
@pytest.mark.django_db
class TestTurnstile:
    def test_missing_invalid_and_replayed_tokens_are_rejected(
        self,
        traveler,
        orange,
        turnstile_on,
        no_drf_throttle,
    ):
        missing = _client().post(OTP_URL, {"phone": CI_PHONE}, format="json")
        invalid = _client().post(
            OTP_URL, {"phone": CI_PHONE}, format="json", HTTP_X_TURNSTILE_TOKEN="bad"
        )
        valid = _client(ip="10.4.0.1").post(
            OTP_URL,
            {"phone": CI_PHONE},
            format="json",
            HTTP_X_TURNSTILE_TOKEN="good-otp",
        )
        replay_other_ip = _client(ip="10.4.0.2").post(
            OTP_URL,
            {"phone": CI_PHONE},
            format="json",
            HTTP_X_TURNSTILE_TOKEN="good-otp",
        )

        assert missing.status_code == 400 and invalid.status_code == 400
        assert valid.status_code == 200
        assert replay_other_ip.status_code == 400
        assert turnstile_on == ["bad", "good-otp"]  # le rejeu n'atteint pas Cloudflare
        assert _otp_sms().count() == 1
        reasons = {e.details["reason"] for e in _events(SecurityEventKind.TURNSTILE_FAILED)}
        assert reasons == {"missing", "invalid", "replay"}

    def test_action_mismatch_is_rejected(self, traveler, orange, turnstile_on, no_drf_throttle):
        # Jeton valide mais émis pour l'inscription, présenté sur l'OTP.
        resp = _client().post(
            OTP_URL, {"phone": CI_PHONE}, format="json", HTTP_X_TURNSTILE_TOKEN="good-reg"
        )
        assert resp.status_code == 400
        assert not _otp_sms().exists()

    def test_public_registration_requires_turnstile(self, turnstile_on, entry_point):
        resp = _client().post(REGISTER_URL, {}, format="json")
        assert resp.status_code == 400
        assert "anti-robot" in resp.data["detail"]
        ok = _client().post(REGISTER_URL, {}, format="json", HTTP_X_TURNSTILE_TOKEN="good-reg")
        assert ok.status_code == 400 and "anti-robot" not in str(
            ok.data
        )  # validation métier atteinte


# ===========================================================================
# 3. Inscriptions massives
# ===========================================================================
@pytest.mark.django_db
class TestMassRegistration:
    @pytest.fixture(autouse=True)
    def _no_drf(self, monkeypatch):
        from apps.ebola.public_views import PublicTravelerRegisterView

        monkeypatch.setattr(PublicTravelerRegisterView, "throttle_classes", [])

    def test_registrations_per_ip_are_capped(self, settings, entry_point):
        settings.PUBLIC_RATE_LIMITS = {**settings.PUBLIC_RATE_LIMITS, "registration_ip": (2, 3600)}
        codes = [
            _client(ip="10.5.0.1").post(REGISTER_URL, {}, format="json").status_code
            for _ in range(3)
        ]
        assert codes == [400, 400, 429]
        assert (
            _events(SecurityEventKind.RATE_LIMITED).filter(source="public_registration").count()
            == 1
        )

    def test_registrations_per_phone_are_capped_across_ips(self, settings, entry_point):
        # Le plafond par numéro s'applique avant toute validation : une rafale
        # de fiches (même incomplètes) sur un numéro est bloquée, quelle que
        # soit l'IP d'origine.
        settings.PUBLIC_RATE_LIMITS = {
            **settings.PUBLIC_RATE_LIMITS,
            "registration_phone": (2, 86400),
        }
        payload = {"identite": {"phone_mobile": "+33612345678"}}
        codes = [
            _client(ip=f"10.6.0.{i}").post(REGISTER_URL, payload, format="json").status_code
            for i in range(3)
        ]
        assert codes == [400, 400, 429]


# ===========================================================================
# 4. Appels concurrents (vraies transactions, un thread = une connexion)
# ===========================================================================
@pytest.fixture
def live_db(django_db_setup, django_db_blocker):
    """Autocommit sans flush final (`--reuse-db`) : chaque test nettoie ses lignes."""
    with django_db_blocker.unblock():
        yield


def test_concurrent_sends_never_exceed_the_number_quota(live_db, guard, monkeypatch):
    monkeypatch.setattr(
        "apps.notifications.tasks.send_notification_task.delay", lambda *a, **k: None
    )
    guard["PER_NUMBER"]["standard"] = (3, 12)
    phone = "+33698765432"
    barrier = threading.Barrier(10)
    results, errors = [], []

    def worker():
        try:
            barrier.wait(timeout=10)
            results.append(_sms(recipient=phone))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join(30)
        assert not errors, errors
        assert sum(1 for r in results if r.ok) == 3
        assert {r.error_code for r in results if not r.ok} == {ErrorCode.SMS_QUOTA_EXCEEDED}
        assert Notification.objects.filter(normalized_phone=phone).count() == 3
    finally:
        Notification.all_objects.filter(normalized_phone=phone).delete()
        SmsSecurityEvent.all_objects.filter(phone_masked__startswith=phone[:6]).delete()


# ===========================================================================
# 5. Budget, coupe-circuit, urgences, échec fournisseur
# ===========================================================================
@pytest.mark.django_db
class TestBudgetAndProviders:
    def test_daily_budget_trips_the_breaker_holds_and_alerts(
        self,
        superadmin,
        orange,
        guard,
        django_capture_on_commit_callbacks,
    ):
        guard["BUDGET_DAILY"] = 3
        with django_capture_on_commit_callbacks(execute=True):
            results = [_sms(recipient=f"+22507080900{i:02d}") for i in range(5)]

        statuses = [Notification.objects.get(pk=r.notification_id).status for r in results]
        assert statuses == [NotificationStatus.SENT] * 3 + [NotificationStatus.ON_HOLD] * 2
        assert orange.call_count == 3  # plus aucune dépense après le plafond
        states = dict(ProviderAvailability.objects.values_list("provider", "state"))
        assert states == {
            "orange_ci": ProviderState.BUDGET_EXCEEDED,
            "twilio": ProviderState.BUDGET_EXCEEDED,
        }
        assert _events(SecurityEventKind.BUDGET_EXCEEDED).count() == 1
        assert _events(SecurityEventKind.BUDGET_ALERT).count() == 1
        subjects = list(
            Notification.objects.filter(message_type=MessageType.ADMIN_NOTICE).values_list(
                "subject", flat=True
            )
        )
        assert sum("budget SMS atteint" in s for s in subjects) == 2  # 1 par fournisseur
        assert sum("Budget SMS journalier" in s for s in subjects) == 1  # alerte à 80 %

        # Les urgences médicales restent prioritaires (enveloppe dédiée).
        urgent = _sms(
            recipient="+2250708090999",
            body="Alerte symptôme critique",
            message_type=MessageType.SYMPTOM_ALERT,
        )
        assert Notification.objects.get(pk=urgent.notification_id).status == NotificationStatus.SENT

    def test_urgent_envelope_is_not_unlimited(self, superadmin, orange, guard):
        guard["URGENT_DAILY"] = 2
        results = [
            _sms(
                recipient=f"+22507080901{i:02d}",
                body="Alerte",
                message_type=MessageType.SYMPTOM_ALERT,
            )
            for i in range(3)
        ]
        assert [r.ok for r in results] == [True, True, False]
        assert results[2].error_code == ErrorCode.URGENT_CAP
        assert _events(SecurityEventKind.URGENT_CAP).count() == 1

    def test_provider_cap_suspends_only_that_provider(self, orange, twilio, guard):
        guard["PER_PROVIDER_DAY"] = {"orange_ci": 1000, "twilio": 2}
        intl = [_sms(recipient=f"+3361234560{i}") for i in range(3)]
        ci = _sms(recipient=CI_PHONE)

        assert [Notification.objects.get(pk=r.notification_id).status for r in intl] == [
            NotificationStatus.SENT,
            NotificationStatus.SENT,
            NotificationStatus.ON_HOLD,
        ]
        assert twilio.call_count == 2
        assert Notification.objects.get(pk=ci.notification_id).status == NotificationStatus.SENT
        assert (
            ProviderAvailability.objects.get(provider=Provider.TWILIO).state
            == ProviderState.BUDGET_EXCEEDED
        )
        assert not ProviderAvailability.objects.filter(provider=Provider.ORANGE_CI).exists()

    def test_twilio_balance_exhausted_suspends_without_costly_retries(self, twilio, guard):
        twilio.return_value = TwilioSendResult(
            ok=False,
            error='Twilio HTTP 400 : {"message": "Account balance is too low"}',
        )
        first = _sms(recipient="+33611111111")
        second = _sms(recipient="+33622222222")
        assert (
            Notification.objects.get(pk=first.notification_id).status == NotificationStatus.ON_HOLD
        )
        assert (
            Notification.objects.get(pk=second.notification_id).status == NotificationStatus.ON_HOLD
        )
        assert twilio.call_count == 1
        assert (
            ProviderAvailability.objects.get(provider=Provider.TWILIO).state
            == ProviderState.QUOTA_EXHAUSTED
        )

    def test_redis_outage_falls_back_to_database_counts(self, orange, guard, monkeypatch):
        monkeypatch.setattr("apps.notifications.services.sms_guard._incr", lambda *a, **k: None)
        guard["PER_NUMBER"]["standard"] = (6, 2)
        results = [_sms(recipient=CI_PHONE) for _ in range(3)]
        assert [r.ok for r in results] == [True, True, False]

    def test_international_spike_is_logged_and_alerted_once(self, superadmin, twilio, guard):
        guard["SPIKE_INTL_PREFIX_HOUR"] = 3
        for i in range(6):
            _sms(recipient=f"+4477009000{i:02d}")
        assert _events(SecurityEventKind.SPIKE).count() == 1
        assert (
            Notification.objects.filter(
                message_type=MessageType.ADMIN_NOTICE,
                subject__icontains="Pic anormal",
            ).count()
            == 1
        )

    def test_country_allowlist(self, orange, twilio, guard):
        guard["ALLOWED_CALLING_CODES"] = ["33"]
        assert _sms(recipient="+15145550000").error_code == ErrorCode.COUNTRY_BLOCKED
        assert _sms(recipient="+33612000000").ok
        assert _sms(recipient=CI_PHONE).ok


# ===========================================================================
# 6. Routage strict et RBAC des envois
# ===========================================================================
@pytest.mark.django_db
class TestRoutingAndRbac:
    def test_orange_never_used_for_international_numbers(self, orange):
        forced = _sms(recipient="+33612345678", force_provider=Provider.ORANGE_CI)
        assert not forced.ok and forced.error_code == ErrorCode.NATIONAL_POLICY
        assert _events(SecurityEventKind.ROUTING_BLOCKED).count() == 1

        from apps.notifications.tasks import send_notification_task

        misrouted = Notification.objects.create(
            channel=Channel.SMS,
            recipient="+33612345678",
            normalized_phone="+33612345678",
            body="x",
            provider=Provider.ORANGE_CI,
            status=NotificationStatus.QUEUED,
        )
        send_notification_task.run(misrouted.pk)
        misrouted.refresh_from_db()
        assert misrouted.error_code == ErrorCode.NATIONAL_POLICY
        assert orange.call_count == 0

    def test_agents_cannot_text_arbitrary_numbers(self, district_agent, traveler, orange):
        client = _client(district_agent)
        free = client.post(
            "/api/v1/notifications/send/",
            {
                "channel": "sms",
                "recipient": "+33612345678",
                "body": "Bonjour",
            },
            format="json",
        )
        other = client.post(
            "/api/v1/notifications/send/",
            {
                "channel": "sms",
                "traveler": traveler.pk,
                "recipient": "+33612345679",
                "body": "Bonjour",
            },
            format="json",
        )
        own = client.post(
            "/api/v1/notifications/send/",
            {
                "channel": "sms",
                "traveler": traveler.pk,
                "recipient": "+225 07 08 09 09 11",
                "body": "Bonjour",
            },
            format="json",
        )

        assert free.status_code == 403 and other.status_code == 403
        assert own.status_code == 201, own.data
        assert _events(SecurityEventKind.RECIPIENT_REJECTED).count() == 2
        assert orange.call_count == 1

    def test_admins_keep_free_recipients(self, superadmin, twilio):
        resp = _client(superadmin).post(
            "/api/v1/notifications/send/",
            {
                "channel": "sms",
                "recipient": "+33612345678",
                "body": "Bonjour",
            },
            format="json",
        )
        assert resp.status_code == 201, resp.data

    def test_followup_notify_rejects_foreign_recipient(
        self, district_agent, traveler, ebola_disease, orange
    ):
        from apps.quarantine.models import QuarantineRecord, QuarantineStatus

        QuarantineRecord.objects.create(
            traveler=traveler,
            disease=ebola_disease,
            started_on=date.today(),
            expected_end_on=date.today() + timedelta(days=21),
            status=QuarantineStatus.ACTIVE,
            address="Cocody",
        )
        url = f"/api/v1/admin/followups/{traveler.public_id}/notify/"
        client = _client(district_agent)
        bad = client.post(
            url, {"channel": "sms", "recipient": "+33612345678", "body": "Bonjour"}, format="json"
        )
        good = client.post(
            url, {"channel": "sms", "recipient": CI_PHONE, "body": "Bonjour"}, format="json"
        )
        assert bad.status_code == 403
        assert good.status_code == 200, good.data
        assert orange.call_count == 1

    def test_security_events_api_is_admin_only(self, district_agent, superadmin, orange, guard):
        guard["PER_NUMBER"]["standard"] = (1, 12)
        _sms(recipient=CI_PHONE)
        _sms(recipient=CI_PHONE)
        assert (
            _client(district_agent).get("/api/v1/notifications/security-events/").status_code == 403
        )
        rows = _client(superadmin).get("/api/v1/notifications/security-events/").data["results"]
        assert rows[0]["kind"] == SecurityEventKind.NUMBER_QUOTA
        assert CI_PHONE not in str(rows[0])  # numéro jamais exposé en clair


@pytest.mark.django_db
def test_legacy_quarantine_reminders_do_not_duplicate(traveler, ebola_disease, orange):
    from apps.companion import tasks as companion_tasks
    from apps.companion.models import ConsentScope
    from apps.companion.services import record_consent
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus
    from apps.quarantine.tasks import send_daily_reminders

    QuarantineRecord.objects.create(
        traveler=traveler,
        disease=ebola_disease,
        started_on=date.today() - timedelta(days=3),
        expected_end_on=date.today() + timedelta(days=18),
        status=QuarantineStatus.ACTIVE,
        address="Cocody",
    )
    record_consent(
        traveler=traveler, scope=ConsentScope.PUSH_NOTIFICATIONS, granted=True, version="v1.0"
    )

    companion_tasks.send_daily_checkin_reminders.run()
    send_daily_reminders()

    assert Notification.objects.filter(traveler=traveler, channel=Channel.SMS).count() == 1
