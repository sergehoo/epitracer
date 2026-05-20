"""Tests d'intégration de l'API Ebola."""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(superadmin):
    c = APIClient()
    c.force_authenticate(user=superadmin)
    return c


def test_create_ebola_investigation(client, traveler, entry_point, ebola_disease):
    resp = client.post(
        "/api/v1/ebola/investigations/",
        {
            "traveler": traveler.id,
            "entry_point": entry_point.id,
            "status": "new",
            "notes": "Test enquête",
            "exposure": {
                "visited_outbreak_country": True,
                "contact_with_confirmed_case": True,
                "attended_funerals": False,
            },
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    case = resp.data["case_number"]
    assert case.startswith("EBO-")

    # Re-lire pour vérifier le scoring appliqué
    detail = client.get(f"/api/v1/ebola/investigations/{case}/")
    assert detail.status_code == 200
    assert detail.data["risk_score"] >= 60
    assert detail.data["risk_level"] in {"high", "critical"}


def test_recompute_score_endpoint(client, traveler, entry_point, ebola_disease):
    resp = client.post(
        "/api/v1/ebola/investigations/",
        {"traveler": traveler.id, "entry_point": entry_point.id, "status": "new"},
        format="json",
    )
    case = resp.data["case_number"]
    r = client.post(f"/api/v1/ebola/investigations/{case}/recompute-score/")
    assert r.status_code == 200
    assert "risk_score" in r.data
