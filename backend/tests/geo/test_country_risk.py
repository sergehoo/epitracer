"""Niveaux de risque pays : règles métier, historique, API admin, surveillance, dashboard."""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, RoleAssignment, RoleCode
from apps.geo.models import Country, CountryRiskAssessment
from apps.geo.services import (
    alert_on_arrival_from_risk_country,
    close_risk_assessment,
    current_assessments,
    record_risk_assessment,
    refresh_country_risk,
    resolve_country,
)
from apps.surveillance.models import HealthAlert
from apps.travelers.models import TravelHistoryEntry

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()
SOURCE = "Bulletin OMS DON test"


@pytest.fixture
def niger(db) -> Country:
    return Country.objects.get(code="NE")


@pytest.fixture
def admin_client(superadmin):
    c = APIClient()
    c.force_authenticate(user=superadmin)
    return c


@pytest.fixture
def observer_client(db, django_user_model, roles):
    user = django_user_model.objects.create_user(
        email="obs@example.ci",
        username="obs@example.ci",
        password="StrongPwd!2026",
    )
    RoleAssignment.objects.create(
        user=user, role=Role.objects.get(code=RoleCode.OBSERVER), is_active=True
    )
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# --------------------------------------------------------------------------- règles


def test_level_above_normal_requires_a_validated_alert_source(niger, ebola_disease):
    with pytest.raises(ValidationError) as exc:
        record_risk_assessment(
            country=niger,
            disease=ebola_disease,
            risk_level="high",
            justification="Cas signalés",
        )
    assert "source_reference" in exc.value.message_dict
    a = record_risk_assessment(
        country=niger,
        disease=ebola_disease,
        risk_level="high",
        justification="Cas signalés",
        source_reference=SOURCE,
    )
    assert a.pk and niger.risk_level == "high"


def test_justification_is_mandatory(niger):
    with pytest.raises(ValidationError) as exc:
        record_risk_assessment(country=niger, risk_level="normal", justification="  ")
    assert "justification" in exc.value.message_dict


def test_dismissed_alert_cannot_justify_a_level(niger):
    alert = HealthAlert.objects.create(code="x", title="Rumeur infondée", status="dismissed")
    with pytest.raises(ValidationError) as exc:
        record_risk_assessment(
            country=niger,
            risk_level="moderate",
            justification="j",
            source_alert=alert,
        )
    assert "source_alert" in exc.value.message_dict


def test_new_level_closes_previous_one_and_keeps_history(niger, ebola_disease):
    first = record_risk_assessment(
        country=niger,
        disease=ebola_disease,
        risk_level="moderate",
        justification="Alerte 1",
        source_reference=SOURCE,
        valid_from=TODAY - timedelta(days=10),
    )
    second = record_risk_assessment(
        country=niger,
        disease=ebola_disease,
        risk_level="critical",
        justification="Alerte 2",
        source_reference=SOURCE,
    )
    first.refresh_from_db()
    assert first.valid_until == TODAY - timedelta(days=1)
    assert list(current_assessments().filter(country=niger)) == [second]
    assert CountryRiskAssessment.objects.filter(country=niger).count() == 2
    assert first.history.first().history_change_reason.startswith("Remplacée")
    niger.refresh_from_db()
    assert niger.risk_level == "critical"


def test_new_level_supersedes_a_future_one(niger):
    future = record_risk_assessment(
        country=niger,
        risk_level="high",
        justification="Prévu",
        source_reference=SOURCE,
        valid_from=TODAY + timedelta(days=5),
    )
    now = record_risk_assessment(
        country=niger, risk_level="moderate", justification="Révisé", source_reference=SOURCE
    )
    future.refresh_from_db()
    assert future.superseded_by == now


def test_country_level_is_the_highest_across_diseases(niger, ebola_disease):
    record_risk_assessment(
        country=niger,
        disease=ebola_disease,
        risk_level="high",
        justification="j",
        source_reference=SOURCE,
    )
    record_risk_assessment(
        country=niger, risk_level="moderate", justification="j", source_reference=SOURCE
    )
    niger.refresh_from_db()
    assert niger.risk_level == "high"
    assert niger.risk_for_diseases == ["EBOLA"]


def test_level_returns_to_normal_after_validity_end(niger):
    record_risk_assessment(
        country=niger,
        risk_level="high",
        justification="j",
        source_reference=SOURCE,
        valid_until=TODAY,
    )
    niger.refresh_from_db()
    assert niger.risk_level == "high"
    refresh_country_risk(niger, on=TODAY + timedelta(days=1))
    assert niger.risk_level == "normal"


def test_close_requires_reason_and_restores_normal(niger):
    a = record_risk_assessment(
        country=niger, risk_level="high", justification="j", source_reference=SOURCE
    )
    with pytest.raises(ValidationError):
        close_risk_assessment(a, reason="")
    close_risk_assessment(a, valid_until=TODAY, reason="Fin d'épidémie déclarée")
    refresh_country_risk(niger, on=TODAY + timedelta(days=1))
    assert niger.risk_level == "normal"
    assert a.history.first().history_change_reason == "Fin d'épidémie déclarée"


def test_resolve_country_accepts_iso2_and_iso3_any_case():
    assert resolve_country("ne").code == "NE"
    assert resolve_country("GMB").code == "GM"
    assert resolve_country("") is None
    assert resolve_country("XXXX") is None


# --------------------------------------------------------------------------- API


def test_admin_records_a_level_through_the_api(admin_client, niger, ebola_disease):
    resp = admin_client.post(
        "/api/v1/geo/country-risks/",
        {
            "country": "NE",
            "disease": "EBOLA",
            "risk_level": "high",
            "justification": "Cas confirmés à Niamey",
            "source_reference": SOURCE,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["is_current"] is True
    assert resp.data["decided_by_email"] == "admin@example.ci"

    countries = admin_client.get("/api/v1/geo/countries/?is_monitored=true&page_size=300").data
    rows = countries.get("results", countries)
    ne = next(c for c in rows if c["code"] == "NE")
    assert ne["risk_level"] == "high"
    assert [r["disease_code"] for r in ne["current_risks"]] == ["EBOLA"]


def test_api_rejects_level_without_source(admin_client, niger):
    resp = admin_client.post(
        "/api/v1/geo/country-risks/",
        {
            "country": "NE",
            "risk_level": "critical",
            "justification": "j",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "source_reference" in resp.data["error"]["details"]


def test_non_admin_cannot_change_levels(observer_client, niger):
    resp = observer_client.post(
        "/api/v1/geo/country-risks/",
        {
            "country": "NE",
            "risk_level": "normal",
            "justification": "j",
        },
        format="json",
    )
    assert resp.status_code == 403
    assert observer_client.get("/api/v1/geo/country-risks/").status_code == 200


def test_country_risk_level_cannot_be_patched_directly(admin_client, niger):
    resp = admin_client.patch(
        f"/api/v1/geo/countries/{niger.pk}/", {"risk_level": "critical"}, format="json"
    )
    assert resp.status_code == 200
    niger.refresh_from_db()
    assert niger.risk_level == "normal"


def test_api_refuses_duplicate_iso_codes(admin_client):
    resp = admin_client.post(
        "/api/v1/geo/countries/",
        {
            "code": "zz",
            "code3": "ner",
            "name": "Doublon Niger",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "code3" in resp.data["error"]["details"]
    resp = admin_client.post(
        "/api/v1/geo/countries/", {"code": "ne", "name": "Doublon"}, format="json"
    )
    assert resp.status_code == 400
    assert "code" in resp.data["error"]["details"]


def test_history_and_close_endpoints(admin_client, niger):
    record_risk_assessment(
        country=niger,
        risk_level="moderate",
        justification="1",
        source_reference=SOURCE,
        valid_from=TODAY - timedelta(days=3),
    )
    current = record_risk_assessment(
        country=niger, risk_level="high", justification="2", source_reference=SOURCE
    )

    history = admin_client.get(f"/api/v1/geo/countries/{niger.pk}/risk-history/").data
    assert [h["risk_level"] for h in history] == ["high", "moderate"]

    assert (
        admin_client.post(
            f"/api/v1/geo/country-risks/{current.uuid}/close/", {}, format="json"
        ).status_code
        == 400
    )
    resp = admin_client.post(
        f"/api/v1/geo/country-risks/{current.uuid}/close/",
        {"reason": "Levée de l'alerte"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert resp.data["valid_until"] == TODAY.isoformat()


# ------------------------------------------------------------------ surveillance


def test_arrival_from_high_risk_country_raises_an_alert(traveler, niger, ebola_disease):
    TravelHistoryEntry.objects.create(traveler=traveler, role="origin", country=niger)
    assert alert_on_arrival_from_risk_country(traveler) is None  # Niger au niveau normal

    record_risk_assessment(
        country=niger,
        disease=ebola_disease,
        risk_level="critical",
        justification="j",
        source_reference=SOURCE,
    )
    alert = alert_on_arrival_from_risk_country(traveler)
    assert alert is not None
    assert (alert.code, alert.severity, alert.disease) == (
        "arrival_from_risk_country",
        "critical",
        ebola_disease,
    )
    assert alert.metadata["risks"][0]["country_code"] == "NE"


@pytest.fixture
def pass_keys(tmp_path, monkeypatch, settings):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from apps.health_pass import crypto

    priv = Ed25519PrivateKey.generate()
    (tmp_path / "priv.pem").write_bytes(
        priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (tmp_path / "pub.pem").write_bytes(
        priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    monkeypatch.setitem(settings.HEALTHPASS, "PRIVATE_KEY_PATH", str(tmp_path / "priv.pem"))
    monkeypatch.setitem(settings.HEALTHPASS, "PUBLIC_KEY_PATH", str(tmp_path / "pub.pem"))
    crypto._load_private_key.cache_clear()
    crypto._load_public_key.cache_clear()
    yield
    crypto._load_private_key.cache_clear()
    crypto._load_public_key.cache_clear()


def test_public_form_accepts_new_countries_and_alerts(pass_keys, entry_point, ebola_disease, niger):
    cache.clear()  # quota anti-abus du formulaire public
    record_risk_assessment(
        country=niger,
        disease=ebola_disease,
        risk_level="high",
        justification="j",
        source_reference=SOURCE,
    )
    payload = {
        "voyage": {
            "arrival_date": TODAY.isoformat(),
            "transport_mode": "air",
            "entry_point_code": "ABJ",
        },
        "identite": {
            "last_name": "SOW",
            "first_name": "Awa",
            "gender": "F",
            "phone_mobile": "+22790000000",
            "nationality_code": "NER",
        },
        "historique": [
            {"role": "origin", "country_code": "NE", "city": "Niamey"},
            {"role": "transit", "country_code": "gmb"},
        ],
        "confinement": {"city": "Abidjan"},
        "exposure": {},
        "symptoms": {},
        "declaration": {"truthful_declaration": True},
    }
    resp = APIClient().post("/api/v1/ebola/public/register/", payload, format="json")
    assert resp.status_code == 201, resp.data

    public_id = resp.data["traveler"]["public_id"]
    entries = TravelHistoryEntry.objects.filter(traveler__public_id=public_id)
    assert sorted(entries.values_list("country__code", flat=True)) == ["GM", "NE"]
    assert entries.first().traveler.nationality.code == "NE"
    alert = HealthAlert.objects.get(code="arrival_from_risk_country")
    assert alert.metadata["traveler_public_id"] == public_id


def test_moderate_level_does_not_raise_an_arrival_alert(traveler, niger):
    TravelHistoryEntry.objects.create(traveler=traveler, role="transit", country=niger)
    record_risk_assessment(
        country=niger, risk_level="moderate", justification="j", source_reference=SOURCE
    )
    assert alert_on_arrival_from_risk_country(traveler) is None


# --------------------------------------------------------------------- dashboard


def test_dashboard_filters_and_stats_by_origin_country_risk(
    admin_client, traveler, niger, ebola_disease
):
    cache.clear()
    TravelHistoryEntry.objects.create(traveler=traveler, role="origin", country=niger)
    record_risk_assessment(
        country=niger,
        disease=ebola_disease,
        risk_level="high",
        justification="j",
        source_reference=SOURCE,
    )

    data = admin_client.get("/api/v1/analytics/national/?origin_risk=high&monitored=true").data
    assert data["filters"]["origin_risk"] == "high"
    assert data["kpis"]["travelers_total"] == 1
    assert data["arrivals_by_origin_risk"]["high"] == 1
    ne = next(c for c in data["monitored_countries"] if c["code"] == "NE")
    assert (ne["risk_level"], ne["arrivals_period"]) == ("high", 1)
    assert data["monitored_countries"][0]["code"] == "NE"  # pays le plus à risque en tête
    assert data["top_origins"][0]["country__risk_level"] == "high"

    assert (
        admin_client.get("/api/v1/analytics/national/?origin_risk=critical").data["kpis"][
            "travelers_total"
        ]
        == 0
    )
