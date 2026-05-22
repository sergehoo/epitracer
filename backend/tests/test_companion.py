"""Tests du module Companion (consentement, check-in, géoloc, push, admin).

Couvre :
- Services : append-only consents, garde de consentement pour géoloc,
  matrice de severité des check-ins.
- Endpoints publics : consent, checkin, location ping, push subscribe.
- Endpoints admin : RBAC + audit log.

Les tests utilisent le `traveler` fixture du conftest et créent les
QuarantineRecord nécessaires à la volée.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.companion.models import (
    ConsentScope,
    DataAccessLog,
    PrivacyConsent,
    PushSubscription,
    TravelerLocationPing,
)
from apps.companion import services
from apps.diseases.models import Disease


pytestmark = pytest.mark.django_db


# ----------------------------------------------------------------------------
# Fixtures locales
# ----------------------------------------------------------------------------


@pytest.fixture
def quarantine(db, traveler, ebola_disease):
    """Crée une quarantaine active de J0..J21 pour le voyageur."""
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus
    return QuarantineRecord.objects.create(
        traveler=traveler,
        disease=ebola_disease,
        started_on=date.today(),
        expected_end_on=date.today() + timedelta(days=21),
        status=QuarantineStatus.ACTIVE,
        address="Cocody, II Plateaux",
    )


@pytest.fixture
def api():
    return APIClient()


# ============================================================================
# 1. Services
# ============================================================================


def test_record_consent_creates_new_row(traveler):
    c1 = services.record_consent(
        traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True,
        version="v1", ip="1.2.3.4", user_agent="UA-test",
    )
    assert c1.granted is True
    assert c1.revoked_at is None
    assert services.has_consent(traveler, ConsentScope.GEOLOCATION) is True


def test_record_consent_revocation_does_not_modify_original(traveler):
    """Append-only : retirer un consentement crée une NOUVELLE ligne."""
    services.record_consent(
        traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True,
    )
    services.record_consent(
        traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=False,
        revocation_reason="changé d'avis",
    )
    # 2 lignes existent
    assert PrivacyConsent.objects.filter(traveler=traveler, scope=ConsentScope.GEOLOCATION).count() == 2
    # Plus de consentement actif
    assert services.has_consent(traveler, ConsentScope.GEOLOCATION) is False


def test_has_consent_returns_false_for_unknown_scope(traveler):
    assert services.has_consent(traveler, ConsentScope.PUSH_NOTIFICATIONS) is False


# ----------------------------------------------------------------------------
# Géoloc : garde de consentement
# ----------------------------------------------------------------------------


def test_record_location_ping_refuses_without_consent(traveler):
    ping = services.record_location_ping(
        traveler=traveler, latitude=5.345, longitude=-4.024,
    )
    assert ping is None
    assert TravelerLocationPing.objects.count() == 0


def test_record_location_ping_works_with_consent(traveler):
    services.record_consent(
        traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True, version="v1.0",
    )
    ping = services.record_location_ping(
        traveler=traveler, latitude=5.345, longitude=-4.024, accuracy_m=10.0,
    )
    assert ping is not None
    assert ping.consent_version == "v1.0"
    assert float(ping.latitude) == 5.345
    assert TravelerLocationPing.objects.count() == 1


def test_record_location_ping_does_not_work_after_revocation(traveler):
    services.record_consent(traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True)
    services.record_consent(traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=False)
    ping = services.record_location_ping(traveler=traveler, latitude=5, longitude=-4)
    assert ping is None


# ----------------------------------------------------------------------------
# Matrice de sévérité
# ----------------------------------------------------------------------------


@pytest.mark.parametrize("symptoms,expected_sev", [
    ({}, "INFO"),
    ({"intense_fatigue": True}, "LOW"),
    ({"intense_fatigue": True, "severe_headache": True}, "MEDIUM"),
    ({"fever": True}, "MEDIUM"),
    ({"fever": True, "diarrhea_nausea_vomiting": True, "muscle_joint_pain": True}, "HIGH"),
    ({"unexplained_bleeding": True}, "CRITICAL"),
    ({"unexplained_bleeding": True, "fever": True}, "CRITICAL"),
])
def test_evaluate_checkin_severity(symptoms, expected_sev):
    sev, reasons = services.evaluate_checkin_severity(symptoms)
    assert sev == expected_sev


# ----------------------------------------------------------------------------
# Alerte créée à partir d'un check-in
# ----------------------------------------------------------------------------


def test_raise_alert_critical_creates_healthalert(traveler):
    alert = services.raise_alert_from_checkin(
        traveler=traveler, symptoms={"unexplained_bleeding": True},
    )
    assert alert is not None
    assert alert.severity == "CRITICAL"
    assert alert.status == "OPEN"


def test_raise_alert_no_symptom_returns_none(traveler):
    alert = services.raise_alert_from_checkin(traveler=traveler, symptoms={})
    assert alert is None


def test_raise_alert_assistance_request(traveler):
    alert = services.raise_alert_from_checkin(
        traveler=traveler, symptoms={}, needs_assistance=True,
    )
    assert alert is not None
    assert alert.severity == "HIGH"


# ============================================================================
# 2. Endpoints publics
# ============================================================================


# ----- Consent -----


def test_consent_endpoint_creates_row(api, traveler):
    resp = api.post(
        "/api/v1/public/consent/",
        {"public_id": traveler.public_id, "scope": "geolocation",
         "granted": True, "consent_version": "v1.0"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["granted"] is True
    assert PrivacyConsent.objects.filter(traveler=traveler).count() == 1


def test_consent_endpoint_404_for_unknown_traveler(api):
    resp = api.post(
        "/api/v1/public/consent/",
        {"public_id": "TRV-UNKNOWN", "scope": "geolocation", "granted": True},
        format="json",
    )
    assert resp.status_code == 404


# ----- Check-in -----


def test_checkin_ok_creates_dailycheck(api, traveler, quarantine):
    resp = api.post(
        "/api/v1/public/checkin/",
        {"public_id": traveler.public_id, "feeling": "ok"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["ok"] is True
    assert resp.data["alert_created"] is False
    # DailyCheck créé
    assert quarantine.daily_checks.count() == 1


def test_checkin_with_critical_symptom_raises_alert(api, traveler, quarantine):
    resp = api.post(
        "/api/v1/public/checkin/",
        {"public_id": traveler.public_id, "feeling": "symptom",
         "symptoms": {"unexplained_bleeding": True}},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["alert_created"] is True
    assert resp.data["alert_severity"] == "CRITICAL"


def test_checkin_assistance_request_creates_high_alert(api, traveler, quarantine):
    resp = api.post(
        "/api/v1/public/checkin/",
        {"public_id": traveler.public_id, "feeling": "assistance"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["alert_created"] is True
    assert "143" in resp.data["message"]


def test_checkin_with_location_but_no_consent_ignores_position(api, traveler, quarantine):
    resp = api.post(
        "/api/v1/public/checkin/",
        {"public_id": traveler.public_id, "feeling": "ok",
         "latitude": 5.345, "longitude": -4.024},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["location_recorded"] is False
    assert TravelerLocationPing.objects.count() == 0


def test_checkin_with_location_and_consent_records_ping(api, traveler, quarantine):
    services.record_consent(traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True)
    resp = api.post(
        "/api/v1/public/checkin/",
        {"public_id": traveler.public_id, "feeling": "ok",
         "latitude": 5.345, "longitude": -4.024, "accuracy_m": 15.0},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["location_recorded"] is True
    assert TravelerLocationPing.objects.count() == 1


def test_checkin_is_idempotent_per_day(api, traveler, quarantine):
    """Deux check-ins le même jour → un seul DailyCheck (update_or_create)."""
    api.post("/api/v1/public/checkin/",
             {"public_id": traveler.public_id, "feeling": "ok"},
             format="json")
    api.post("/api/v1/public/checkin/",
             {"public_id": traveler.public_id, "feeling": "symptom",
              "symptoms": {"fever": True}},
             format="json")
    assert quarantine.daily_checks.count() == 1
    # Le dernier état remplace le précédent
    check = quarantine.daily_checks.first()
    assert check.has_symptoms is True


# ----- Location ping -----


def test_location_ping_refused_without_consent(api, traveler):
    resp = api.post(
        "/api/v1/public/location/ping/",
        {"public_id": traveler.public_id, "latitude": 5.345, "longitude": -4.024},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["reason"] == "consent_required"


def test_location_ping_works_with_consent(api, traveler):
    services.record_consent(traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True)
    resp = api.post(
        "/api/v1/public/location/ping/",
        {"public_id": traveler.public_id, "latitude": 5.345, "longitude": -4.024,
         "event_type": "manual_share"},
        format="json",
    )
    assert resp.status_code == 201
    assert TravelerLocationPing.objects.count() == 1


# ----- Push -----


def test_push_subscribe_refused_without_consent(api, traveler):
    resp = api.post(
        "/api/v1/public/push/subscribe/",
        {"public_id": traveler.public_id,
         "subscription": {
             "endpoint": "https://fcm.googleapis.com/fcm/send/test",
             "keys": {"p256dh": "abc", "auth": "xyz"},
         }},
        format="json",
    )
    assert resp.status_code == 403
    assert resp.data["reason"] == "consent_required"


def test_push_subscribe_works_with_consent(api, traveler):
    services.record_consent(traveler=traveler, scope=ConsentScope.PUSH_NOTIFICATIONS, granted=True)
    resp = api.post(
        "/api/v1/public/push/subscribe/",
        {"public_id": traveler.public_id,
         "subscription": {
             "endpoint": "https://fcm.googleapis.com/fcm/send/test1",
             "keys": {"p256dh": "abc", "auth": "xyz"},
         },
         "device_type": "mobile"},
        format="json",
    )
    assert resp.status_code == 201
    assert PushSubscription.objects.count() == 1


def test_push_unsubscribe_marks_inactive(api, traveler):
    services.record_consent(traveler=traveler, scope=ConsentScope.PUSH_NOTIFICATIONS, granted=True)
    sub = PushSubscription.objects.create(
        traveler=traveler,
        endpoint="https://fcm.googleapis.com/fcm/send/abcd",
        p256dh="pk", auth="ak", is_active=True,
    )
    resp = api.post(
        "/api/v1/public/push/unsubscribe/",
        {"public_id": traveler.public_id, "endpoint": sub.endpoint},
        format="json",
    )
    assert resp.status_code == 200
    sub.refresh_from_db()
    assert sub.is_active is False


# ----- Follow-up status -----


def test_followup_status_returns_traveler_and_consents(api, traveler, quarantine):
    services.record_consent(traveler=traveler, scope=ConsentScope.PUSH_NOTIFICATIONS, granted=True)
    resp = api.get(f"/api/v1/public/follow-up/status/?public_id={traveler.public_id}")
    assert resp.status_code == 200
    body = resp.data
    assert body["traveler"]["public_id"] == traveler.public_id
    assert body["quarantine"]["active"] is True
    assert body["consents"]["push"] is True
    assert body["consents"]["geolocation"] is False
    assert body["assistance"]["allo_sante"] == "143"


# ============================================================================
# 3. Endpoints admin (RBAC)
# ============================================================================


def test_admin_followups_requires_auth(api):
    resp = api.get("/api/v1/admin/companion/followups/")
    assert resp.status_code in (401, 403)


def test_admin_followups_works_for_superadmin(superadmin, traveler, quarantine):
    c = APIClient()
    c.force_authenticate(user=superadmin)
    resp = c.get("/api/v1/admin/companion/followups/")
    assert resp.status_code == 200, resp.data
    assert "kpis" in resp.data
    assert resp.data["kpis"]["active"] >= 1


def test_admin_traveler_locations_logs_access(superadmin, traveler, quarantine):
    services.record_consent(traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True)
    services.record_location_ping(traveler=traveler, latitude=5.345, longitude=-4.024)

    c = APIClient()
    c.force_authenticate(user=superadmin)
    resp = c.get(
        f"/api/v1/admin/companion/travelers/{traveler.public_id}/locations/?reason=Investigation HA-42",
    )
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    # Vérifie qu'un DataAccessLog a été créé
    log = DataAccessLog.objects.filter(traveler=traveler, resource="location").first()
    assert log is not None
    assert "HA-42" in log.reason
    assert log.accessed_by == superadmin


def test_admin_traveler_access_log_returns_entries(superadmin, traveler, quarantine):
    """L'admin peut voir QUI a consulté les données."""
    services.log_data_access(traveler=traveler, user=superadmin, resource="location", reason="test")
    c = APIClient()
    c.force_authenticate(user=superadmin)
    resp = c.get(f"/api/v1/admin/companion/travelers/{traveler.public_id}/access-log/")
    assert resp.status_code == 200
    assert resp.data["count"] >= 1
