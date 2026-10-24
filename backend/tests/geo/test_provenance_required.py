"""Pays de provenance : obligatoire et jamais perdu.

Constat (export voyageurs du 24/10/2026) : de nombreuses fiches « Non renseigné »
en provenance et nationalité. Causes : pays proposés par le formulaire absents
du référentiel (ignorés sans erreur), champs « origin_* » de l'application
mobile non mappés, obligation uniquement côté navigateur.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.geo.models import Country
from apps.geo.world_countries import WORLD_COUNTRIES
from apps.mobile_api.registration import MobileFormSubmissionView
from apps.reports.traveler_fields import itinerary_row
from apps.travelers.models import Traveler, TravelHistoryEntry

REGISTER_URL = "/api/v1/ebola/public/register/"


def _payload(*, historique, identite=None):
    return {
        "voyage": {"arrival_date": "2026-10-24", "entry_point_code": "ABJ"},
        "identite": {
            "last_name": "MWANGI", "first_name": "Henry", "gender": "M",
            "phone_mobile": "+254722204073", **(identite or {}),
        },
        "historique": historique,
        "confinement": {"city": "Abidjan"},
        "exposure": {},
        "symptoms": {},
        "declaration": {"truthful_declaration": True},
    }


def _post(payload):
    return APIClient().post(REGISTER_URL, payload, format="json")


@pytest.mark.django_db
def test_referential_contains_every_country_offered_by_the_forms():
    codes = set(Country.objects.values_list("code", flat=True))
    assert {code for code, _ in WORLD_COUNTRIES} <= codes
    # Pays ignorés auparavant (absents du référentiel initial)
    assert {"KE", "DE", "CA", "CN", "IN", "ET", "JP", "GB"} <= codes
    assert Country.objects.get(code="KE").name == "Kenya"


@pytest.mark.django_db
def test_registration_without_provenance_is_refused(entry_point):
    missing = _post(_payload(historique=[]))
    only_visited = _post(_payload(historique=[{"role": "visited", "country_code": "FR"}]))

    for resp in (missing, only_visited):
        assert resp.status_code == 400
        assert "provenance est obligatoire" in str(resp.data)
    assert not Traveler.objects.exists()


@pytest.mark.django_db
def test_unknown_country_is_refused_instead_of_silently_dropped(entry_point):
    resp = _post(_payload(historique=[{"role": "origin", "country_code": "ZZ"}]))
    assert resp.status_code == 400
    assert "Pays inconnu" in str(resp.data) and "ZZ" in str(resp.data)

    resp = _post(_payload(
        historique=[{"role": "origin", "country_code": "KE"}],
        identite={"nationality_code": "QQ"},
    ))
    assert resp.status_code == 400
    assert "nationality_code" in str(resp.data)
    assert not Traveler.objects.exists()


@pytest.mark.django_db
def test_kenyan_provenance_and_nationality_are_kept(entry_point, pass_keys):
    resp = _post(_payload(
        historique=[{
            "role": "origin", "country_code": "KE", "city": "Nairobi", "province": "Nairobi",
        }],
        identite={"nationality_code": "KE"},
    ))
    assert resp.status_code == 201, resp.data

    traveler = Traveler.objects.get(public_id=resp.data["traveler"]["public_id"])
    assert traveler.nationality.code == "KE"
    origin = TravelHistoryEntry.objects.get(traveler=traveler, role="origin")
    assert origin.country.code == "KE"
    row = itinerary_row(traveler)
    assert row[1] == "Kenya"  # Pays de provenance
    assert row[3] == "Nairobi"  # Ville ou province de provenance


@pytest.mark.parametrize("country", ["KE", {"code": "KE", "name": "Kenya"}])
def test_mobile_origin_fields_become_the_provenance_step(country):
    payload = MobileFormSubmissionView()._build_legacy_payload(
        {"origin_country": country, "origin_city": "Nairobi", "origin_duration": "12 jours",
         "last_name": "MWANGI"},
        signature_data_url="",
    )
    assert payload["historique"] == [{
        "role": "origin", "country_code": "KE", "city": "Nairobi", "duration_text": "12 jours",
    }]
    assert payload["identite"]["last_name"] == "MWANGI"
