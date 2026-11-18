"""Point d'entrée cohérent avec le moyen de transport.

Avion → aéroport ; bateau → port maritime ou fluvial ; voiture, bus, à pied →
frontière terrestre ; train → point ferroviaire ; « Autre » → sans restriction.
Même règle pour le formulaire public, l'API des agents et l'admin ; les fiches
anciennes incohérentes restent modifiables tant que transport et point ne changent pas.
"""
from __future__ import annotations

import pytest
from django import forms
from rest_framework.test import APIClient

from apps.ebola.serializers import PublicTravelerSubmissionSerializer
from apps.geo.models import EntryPoint, EntryPointType
from apps.travelers.admin import TravelerAdminForm
from apps.travelers.models import Traveler
from apps.travelers.serializers import TravelerSerializer

pytestmark = pytest.mark.django_db

REGISTER_URL = "/api/v1/ebola/public/register/"


@pytest.fixture
def points(country_ci):
    def make(code, type_, is_active=True):
        return EntryPoint.objects.create(
            code=code, name=code, type=type_, country=country_ci, is_active=is_active,
        )

    return {
        "airport": make("ABJ-AIRPORT", EntryPointType.AIRPORT),
        "seaport": make("ABJ-PORT", EntryPointType.SEAPORT),
        "river": make("RIV", EntryPointType.RIVER),
        "land": make("NDA-LAND", EntryPointType.LAND),
        "rail": make("OUA-RAIL", EntryPointType.RAIL),
        "closed": make("OLD-AIRPORT", EntryPointType.AIRPORT, is_active=False),
    }


def _voyage_errors(voyage: dict):
    ser = PublicTravelerSubmissionSerializer()
    try:
        ser.validate_voyage(voyage)
    except Exception as exc:  # noqa: BLE001 — ValidationError attendue
        return exc.detail
    return None


def _payload(voyage: dict) -> dict:
    return {
        "voyage": {"arrival_date": "2026-11-18", **voyage},
        "identite": {"last_name": "KONE", "first_name": "Awa", "gender": "F",
                     "phone_mobile": "+22507080901"},
        "historique": [{"role": "origin", "country_code": "GH"}],
        "confinement": {"city": "Abidjan"},
        "exposure": {}, "symptoms": {},
        "declaration": {"truthful_declaration": True},
    }


# --- Formulaire public (web et application mobile) ------------------------------------

@pytest.mark.parametrize("transport, point", [
    ("plane", "airport"), ("boat", "seaport"), ("boat", "river"),
    ("car", "land"), ("bus", "land"), ("foot", "land"), ("train", "rail"),
    ("other", "seaport"), ("", "airport"),
])
def test_public_compatible_combinations_are_accepted(points, transport, point):
    voyage = {"transport_mode": transport, "entry_point_code": points[point].code}
    assert _voyage_errors(voyage) is None


@pytest.mark.parametrize("transport, point", [
    ("plane", "seaport"), ("plane", "land"), ("boat", "airport"), ("car", "airport"),
    ("bus", "seaport"), ("foot", "rail"), ("train", "land"),
])
def test_public_incompatible_combinations_are_refused(points, transport, point):
    errors = _voyage_errors({"transport_mode": transport, "entry_point_code": points[point].code})
    assert "n'est pas compatible" in str(errors["entry_point_code"])


def test_public_unknown_or_closed_entry_point_is_refused(points):
    unknown = _voyage_errors({"transport_mode": "plane", "entry_point_code": "NOPE"})
    assert "Point d'entrée inconnu" in str(unknown["entry_point_code"])
    bad_id = _voyage_errors({"transport_mode": "plane", "entry_point_id": "abc"})
    assert "Point d'entrée inconnu" in str(bad_id["entry_point_code"])
    closed = _voyage_errors({"transport_mode": "plane", "entry_point_code": points["closed"].code})
    assert "n'est plus ouvert" in str(closed["entry_point_code"])


def test_public_payload_without_entry_point_is_still_accepted(points):
    """Application mobile : point d'entrée saisi en texte libre, non transmis comme code."""
    assert _voyage_errors({"transport_mode": "plane"}) is None
    assert _voyage_errors({}) is None


def test_direct_api_call_with_incoherent_combination_creates_nothing(points):
    resp = APIClient().post(
        REGISTER_URL, _payload({"transport_mode": "plane", "entry_point_code": "ABJ-PORT"}),
        format="json",
    )
    assert resp.status_code == 400
    details = resp.data["error"]["details"]
    assert "n'est pas compatible" in str(details["voyage"]["entry_point_code"])
    assert not Traveler.objects.exists()


def test_direct_api_call_with_coherent_combination_is_registered(points, pass_keys):
    resp = APIClient().post(
        REGISTER_URL, _payload({"transport_mode": "boat", "entry_point_code": "ABJ-PORT"}),
        format="json",
    )
    assert resp.status_code == 201, resp.data
    traveler = Traveler.objects.get(public_id=resp.data["traveler"]["public_id"])
    assert (traveler.transport_mode, traveler.entry_point.code) == ("boat", "ABJ-PORT")


def test_public_list_offers_only_open_entry_points(points):
    resp = APIClient().get("/api/v1/ebola/public/entry-points/")
    assert resp.status_code == 200
    codes = {p["code"]: p["type"] for p in resp.data}
    assert codes["OUA-RAIL"] == "rail" and codes["ABJ-AIRPORT"] == "airport"
    assert "OLD-AIRPORT" not in codes


# --- API des agents (création / modification) -------------------------------------------

def _force(traveler, transport_mode, entry_point):
    """Fiche historique : écrite directement en base, sans aucun contrôle."""
    Traveler.objects.filter(pk=traveler.pk).update(
        transport_mode=transport_mode, entry_point=entry_point,
    )
    traveler.refresh_from_db()


def _agent_update(traveler, data):
    ser = TravelerSerializer(traveler, data=data, partial=True)
    return ser.is_valid(), ser.errors


def test_agent_changing_transport_to_incompatible_is_refused(traveler, points):
    traveler.transport_mode, traveler.entry_point = "plane", points["airport"]
    traveler.save()
    ok, errors = _agent_update(traveler, {"transport_mode": "boat"})
    assert not ok and "n'est pas compatible" in str(errors["entry_point"])
    ok, _ = _agent_update(traveler, {"transport_mode": "boat", "entry_point": points["seaport"].pk})
    assert ok


def test_agent_cannot_choose_a_closed_or_missing_entry_point(traveler, points):
    traveler.transport_mode = "plane"
    traveler.save()
    ok, errors = _agent_update(traveler, {"entry_point": points["closed"].pk})
    assert not ok and "n'est plus ouvert" in str(errors["entry_point"])
    ok, errors = _agent_update(traveler, {"entry_point": 999_999})
    assert not ok and "entry_point" in errors


def test_agent_can_still_edit_an_old_incoherent_record(traveler, points):
    """Fiche historique voiture + port : modifiable tant que transport et point ne changent pas."""
    _force(traveler, "car", points["seaport"])
    ok, errors = _agent_update(traveler, {"profession": "Commerçante"})
    assert ok, errors
    full = TravelerSerializer(traveler).data
    full.update(profession="Enseignante")
    ser = TravelerSerializer(traveler, data=full)
    assert ser.is_valid(), ser.errors


def test_agent_keeps_a_closed_entry_point_already_on_record(traveler, points):
    _force(traveler, "plane", points["closed"])
    ok, errors = _agent_update(traveler, {"transport_mode": "other"})
    assert ok, errors


def test_agent_api_refuses_incoherent_patch(superadmin, traveler, points):
    client = APIClient()
    client.force_authenticate(user=superadmin)
    traveler.transport_mode, traveler.entry_point = "plane", points["airport"]
    traveler.save()
    resp = client.patch(
        f"/api/v1/travelers/{traveler.public_id}/",
        {"entry_point": points["land"].pk}, format="json",
    )
    assert resp.status_code == 400
    assert "n'est pas compatible" in str(resp.data["error"]["details"]["entry_point"])
    traveler.refresh_from_db()
    assert traveler.entry_point == points["airport"]


# --- Administration Django ---------------------------------------------------------------

AdminForm = forms.modelform_factory(
    Traveler, form=TravelerAdminForm, fields=["transport_mode", "entry_point", "profession"],
)


def _admin_form(traveler, **changes):
    data = {"transport_mode": traveler.transport_mode,
            "entry_point": traveler.entry_point_id or "", "profession": traveler.profession}
    data.update(changes)
    return AdminForm(data=data, instance=traveler)


def test_admin_refuses_incompatible_or_closed_entry_point(traveler, points):
    traveler.transport_mode, traveler.entry_point = "plane", points["airport"]
    traveler.save()
    form = _admin_form(traveler, transport_mode="train")
    assert not form.is_valid() and "n'est pas compatible" in form.errors["entry_point"][0]
    form = _admin_form(traveler, entry_point=points["closed"].pk)
    assert not form.is_valid() and "n'est plus ouvert" in form.errors["entry_point"][0]
    form = _admin_form(traveler, transport_mode="train", entry_point=points["rail"].pk)
    assert form.is_valid(), form.errors


def test_admin_can_still_edit_an_old_incoherent_record(traveler, points):
    _force(traveler, "bus", points["seaport"])
    form = _admin_form(traveler, profession="Chauffeur")
    assert form.is_valid(), form.errors
