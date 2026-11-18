"""Pays de l'historique (provenance, transit, séjour récent) : codes ISO du référentiel.

Le Combobox du formulaire n'envoie que des codes ISO alpha-2 ; le serveur refuse
tout pays saisi librement, ramène un code ISO-3 ou en minuscules au code ISO-2,
et laisse intactes les étapes déjà enregistrées.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.ebola.serializers import PublicTravelerSubmissionSerializer
from apps.geo.models import Country
from apps.travelers.models import Traveler, TravelHistoryEntry

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/ebola/public/register/"


def _payload(historique):
    return {
        "voyage": {"arrival_date": "2026-11-18", "entry_point_code": "ABJ"},
        "identite": {"last_name": "MENSAH", "first_name": "Kofi", "gender": "M",
                     "phone_mobile": "+233244000111"},
        "historique": historique,
        "confinement": {"city": "Abidjan"},
        "exposure": {}, "symptoms": {},
        "declaration": {"truthful_declaration": True},
    }


def test_codes_are_normalised_to_iso_alpha2():
    items = [
        {"role": "origin", "country_code": "gh"},
        {"role": "transit", "country_code": "SEN"},  # ISO-3 connu du référentiel
        {"role": "visited", "country_code": "fra"},
    ]
    cleaned = PublicTravelerSubmissionSerializer().validate_historique(items)
    assert [i["country_code"] for i in cleaned] == ["GH", "SN", "FR"]


@pytest.mark.parametrize("role", ["origin", "transit", "visited"])
@pytest.mark.parametrize("typed", ["Ghana", "Wakanda", "G", ""])
def test_free_text_country_is_refused_for_every_role(entry_point, role, typed):
    historique = [{"role": "origin", "country_code": "GH"}]
    historique.append({"role": role, "country_code": typed})
    resp = APIClient().post(REGISTER_URL, _payload(historique), format="json")
    assert resp.status_code == 400
    assert not Traveler.objects.exists()


def test_registration_stores_alpha2_countries_for_each_step(entry_point, pass_keys):
    resp = APIClient().post(REGISTER_URL, _payload([
        {"role": "origin", "country_code": "gh", "city": "Accra", "province": "Greater Accra"},
        {"role": "transit", "country_code": "ma", "city": "Casablanca"},
        {"role": "visited", "country_code": "JP", "city": "Osaka", "province": "Kansai"},
    ]), format="json")
    assert resp.status_code == 201, resp.data
    traveler = Traveler.objects.get(public_id=resp.data["traveler"]["public_id"])
    steps = dict(traveler.travel_history.values_list("role", "country__code"))
    assert steps == {"origin": "GH", "transit": "MA", "visited": "JP"}


def test_existing_history_with_a_retired_code_is_left_untouched(traveler):
    """Données historiques : une étape sur un code retiré (AN) reste lisible et inchangée."""
    retired = Country.objects.get(code="AN")
    entry = TravelHistoryEntry.objects.create(traveler=traveler, role="visited", country=retired)
    # Toujours accepté à la soumission (brouillons existants), jamais proposé par le formulaire.
    cleaned = PublicTravelerSubmissionSerializer().validate_historique(
        [{"role": "origin", "country_code": "AN"}],
    )
    assert cleaned[0]["country_code"] == "AN"
    entry.refresh_from_db()
    assert entry.country.code == "AN"
