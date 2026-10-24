"""Portail public multimaladies : catalogue, publication, annonces, parcours voyageur."""

from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, RoleAssignment, RoleCode
from apps.diseases.catalog import NEW_DISEASES, sync_disease_catalog
from apps.diseases.models import Disease, RiskFactor, Symptom
from apps.geo.models import Country
from apps.geo.services import record_risk_assessment
from apps.medical.models import HealthScreening
from apps.medical.screening import apply_screenings
from apps.portal.models import NoticeKind, NoticeStatus, PublicNotice
from apps.portal.services import publish_disease, publish_notice
from apps.quarantine.models import QuarantineRecord
from apps.travelers.models import Traveler

pytestmark = pytest.mark.django_db

NOW = timezone.now()


@pytest.fixture
def admin_client(superadmin):
    c = APIClient()
    c.force_authenticate(user=superadmin)
    return c


@pytest.fixture
def observer(db, django_user_model, roles):
    user = django_user_model.objects.create_user(
        email="obs@example.ci",
        username="obs@example.ci",
        password="StrongPwd!2026",
    )
    RoleAssignment.objects.create(
        user=user,
        role=Role.objects.get(code=RoleCode.OBSERVER),
        is_active=True,
    )
    return user


@pytest.fixture
def catalog(ebola_disease):
    """Ebola (fixture) + Mpox active ; le catalogue complète les brouillons."""
    Disease.objects.create(code="MPOX", name="Mpox (variole simienne)", surveillance_days=21)
    sync_disease_catalog(Disease, Symptom, RiskFactor)
    return Disease.objects.all()


@pytest.fixture
def mpox(catalog) -> Disease:
    return Disease.objects.get(code="MPOX")


# -------------------------------------------------------------------- catalogue


def test_new_diseases_are_created_inactive_and_unpublished():
    for code in NEW_DISEASES:
        d = Disease.objects.get(code=code)
        assert d.is_active is False
        assert d.is_published is False
        assert d.slug and d.description and d.prevention
    assert not Disease.objects.filter(is_published=True).exists()


def test_catalog_is_idempotent_and_never_overwrites(ebola_disease):
    ebola_disease.description = "Texte validé par l'INHP"
    ebola_disease.save()
    sync_disease_catalog(Disease, Symptom, RiskFactor)
    counts = (Disease.objects.count(), Symptom.objects.count(), RiskFactor.objects.count())
    sync_disease_catalog(Disease, Symptom, RiskFactor)

    assert (Disease.objects.count(), Symptom.objects.count(), RiskFactor.objects.count()) == counts
    ebola_disease.refresh_from_db()
    assert ebola_disease.description == "Texte validé par l'INHP"
    assert ebola_disease.slug == "ebola"
    assert ebola_disease.is_published is False


# ---------------------------------------------------------------- publication


def test_only_published_diseases_are_public(catalog, superadmin):
    client = APIClient()
    assert client.get("/api/v1/public/diseases/").data == []
    assert client.get("/api/v1/public/diseases/mpox/").status_code == 404

    publish_disease(Disease.objects.get(code="MPOX"), superadmin)

    rows = client.get("/api/v1/public/diseases/").data
    assert [r["slug"] for r in rows] == ["mpox"]
    detail = client.get("/api/v1/public/diseases/mpox/").data
    assert detail["under_surveillance"] is True
    assert detail["prevention"] and detail["traveler_recommendations"]
    assert [s["label"] for s in detail["symptoms"]][0] == "Éruption cutanée ou lésions"
    assert detail["followup_days"] == 21


def test_publication_requires_an_authorized_administrator(mpox, observer):
    with pytest.raises(PermissionDenied):
        publish_disease(mpox, observer)
    c = APIClient()
    c.force_authenticate(user=observer)
    assert c.post("/api/v1/diseases/MPOX/publish/").status_code == 403


def test_publication_requires_content(admin_client):
    Disease.objects.create(code="TEST", name="Maladie test", slug="test")
    resp = admin_client.post("/api/v1/diseases/TEST/publish/")
    assert resp.status_code == 400
    assert "description" in resp.data["error"]["details"]


def test_publish_and_unpublish_through_the_admin_api(admin_client, mpox):
    resp = admin_client.post("/api/v1/diseases/MPOX/publish/")
    assert resp.status_code == 200, resp.data
    assert resp.data["is_published"] is True
    assert admin_client.post("/api/v1/diseases/MPOX/unpublish/").data["is_published"] is False
    # is_published n'est pas modifiable directement
    admin_client.patch("/api/v1/diseases/MPOX/", {"is_published": True}, format="json")
    mpox.refresh_from_db()
    assert mpox.is_published is False


def test_public_filters(catalog, superadmin):
    for d in Disease.objects.filter(code__in=["MPOX", "DENGUE"]):
        publish_disease(d, superadmin)
    client = APIClient()
    active = client.get("/api/v1/public/diseases/?active=true").data
    assert [r["slug"] for r in active] == ["mpox"]
    vector = client.get("/api/v1/public/diseases/?transmission=vector").data
    assert [r["slug"] for r in vector] == ["dengue"]
    # La recherche porte sur le nom et la description
    assert [r["slug"] for r in client.get("/api/v1/public/diseases/?q=moustique").data] == [
        "dengue"
    ]
    assert client.get("/api/v1/public/diseases/?q=introuvable").data == []


def test_translations_are_served_when_available(mpox, superadmin):
    mpox.public_translations = {"en": {"name": "Mpox (monkeypox)"}}
    mpox.save()
    publish_disease(mpox, superadmin)
    client = APIClient()
    assert client.get("/api/v1/public/diseases/mpox/?lang=en").data["name"] == "Mpox (monkeypox)"
    assert client.get("/api/v1/public/diseases/mpox/").data["name"] == "Mpox (variole simienne)"


# ------------------------------------------------------------------- annonces


def _notice(**kw):
    defaults = {"kind": NoticeKind.ALERT, "title": "Alerte", "summary": "Résumé"}
    return PublicNotice.objects.create(**{**defaults, **kw})


def test_only_published_notices_in_validity_period_are_visible(superadmin):
    visible = _notice(title="Visible")
    publish_notice(visible, superadmin)
    _notice(title="Brouillon")
    _notice(title="Expirée", status=NoticeStatus.PUBLISHED, valid_until=NOW - timedelta(days=1))
    _notice(title="Future", status=NoticeStatus.PUBLISHED, valid_from=NOW + timedelta(days=2))
    _notice(title="Archivée", status=NoticeStatus.ARCHIVED)

    titles = [n["title"] for n in APIClient().get("/api/v1/public/notices/").data]
    assert titles == ["Visible"]


def test_notice_workflow_through_the_admin_api(admin_client, observer, mpox):
    resp = admin_client.post(
        "/api/v1/portal/notices/",
        {
            "kind": "recommendation",
            "title": "Voyageurs en provenance de RDC",
            "summary": "Surveillez votre température 21 jours.",
            "disease": "MPOX",
            "countries": ["CD"],
            "status": "published",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["status"] == "draft"  # le statut ne se force pas à la création
    uuid = resp.data["uuid"]
    assert APIClient().get("/api/v1/public/notices/").data == []

    assert admin_client.post(f"/api/v1/portal/notices/{uuid}/publish/").status_code == 200
    public = APIClient().get("/api/v1/public/notices/?kind=recommendation").data
    assert public[0]["countries"] == [{"code": "CD", "name": Country.objects.get(code="CD").name}]
    assert public[0]["disease"] is None  # fiche Mpox non publiée : pas de lien

    obs = APIClient()
    obs.force_authenticate(user=observer)
    assert obs.post("/api/v1/portal/notices/", {"kind": "alert", "title": "x"}).status_code == 403


# ---------------------------------------------------------- parcours voyageur


def test_registration_config_groups_contact_questions_and_dedups_symptoms(catalog):
    data = APIClient().get("/api/v1/public/registration-config/").data
    assert data["ebola_questionnaire"] is True
    assert [d["code"] for d in data["diseases"]] == ["MPOX"]  # Dengue, rougeole… inactives
    mpox_cfg = data["diseases"][0]
    assert mpox_cfg["contact_exposures"] == [
        {"code": "contact_lesions", "label": mpox_cfg["contact_exposures"][0]["label"]},
    ]
    assert mpox_cfg["specific_exposures"] == []
    assert mpox_cfg["ask_specific_exposures"] == "if_risk_itinerary"
    assert mpox_cfg["followup_days"] == 21
    # « Fièvre » et « douleurs musculaires » sont dans le tronc commun : pas reposées
    extra = [s["code"] for s in data["extra_symptoms"]]
    assert extra == ["rash", "swollen_lymph_nodes"]
    assert "fever" in data["common_symptom_fields"]["fever"]


def test_risk_countries_drive_specific_questions(catalog, mpox):
    cd = Country.objects.get(code="CD")
    record_risk_assessment(
        country=cd,
        disease=mpox,
        risk_level="high",
        justification="j",
        source_reference="Bulletin OMS",
    )
    data = APIClient().get("/api/v1/public/registration-config/").data
    assert data["diseases"][0]["risk_countries"] == ["CD"]


def test_inactive_disease_is_never_screened(traveler, catalog):
    apply_screenings(traveler, [{"disease": "DENGUE", "exposures": ["dengue_area_stay"]}])
    assert not QuarantineRecord.objects.filter(traveler=traveler).exists()
    assert not HealthScreening.objects.exists()


def _register(payload_overrides=None):
    payload = {
        "voyage": {"arrival_date": NOW.date().isoformat(), "entry_point_code": "ABJ"},
        "identite": {"last_name": "KONE", "first_name": "Ali", "gender": "M"},
        "historique": [{"role": "origin", "country_code": "GH"}],
        "confinement": {"city": "Abidjan"},
        "exposure": {},
        "symptoms": {},
        "declaration": {"truthful_declaration": True},
        **(payload_overrides or {}),
    }
    return APIClient().post("/api/v1/ebola/public/register/", payload, format="json")


def test_public_registration_with_several_diseases(pass_keys, entry_point, mpox):
    resp = _register({"screenings": [{"disease": "MPOX", "exposures": ["contact_lesions"]}]})
    assert resp.status_code == 201, resp.data
    assert resp.data["pass"]["qr_token"]
    assert [f["disease_code"] for f in resp.data["followups"]] == ["MPOX"]
    assert resp.data["review_pending"] is False

    traveler = Traveler.objects.get(public_id=resp.data["traveler"]["public_id"])
    assert Traveler.objects.count() == 1
    assert sorted(traveler.quarantines.values_list("disease__code", flat=True)) == ["EBOLA", "MPOX"]
    screening = traveler.health_screenings.get()
    assert (screening.decision, screening.answers["exposures"]) == ("followup", ["contact_lesions"])

    # Le pass public liste un suivi par maladie pour la même identité
    pass_data = APIClient().get(f"/api/v1/ebola/public/pass/{traveler.public_id}/").data
    assert sorted(f["disease_name"] for f in pass_data["followups"]) == [
        "Maladie à virus Ebola",
        "Mpox (variole simienne)",
    ]


def test_legacy_payload_without_screenings_still_accepted(pass_keys, entry_point, ebola_disease):
    """Compatibilité : un client ancien (sans screenings / symptom_codes) reste servi."""
    resp = _register()
    assert resp.status_code == 201, resp.data
    assert resp.data["investigation"]["case_number"].startswith("EBO-")
    assert resp.data["followups"] == []


# ------------------------------------------- permissions, brouillons, seed


def _client_with_role(django_user_model, code: str) -> APIClient:
    user = django_user_model.objects.create_user(
        email=f"{code.lower()}@example.ci",
        username=f"{code.lower()}@example.ci",
        password="StrongPwd!2026",
    )
    RoleAssignment.objects.create(user=user, role=Role.objects.get(code=code), is_active=True)
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.mark.parametrize(
    "role,expected",
    [
        (RoleCode.INHP, 200),
        (RoleCode.MINISTRY, 200),
        (RoleCode.DISTRICT, 403),
        (RoleCode.ENTRY_POINT, 403),
        (RoleCode.OBSERVER, 403),
    ],
)
def test_only_authorized_roles_can_publish(mpox, django_user_model, roles, role, expected):
    client = _client_with_role(django_user_model, role)
    assert client.post("/api/v1/diseases/MPOX/publish/").status_code == expected
    notice = PublicNotice.objects.create(kind=NoticeKind.ALERT, title="A", summary="B")
    assert client.post(f"/api/v1/portal/notices/{notice.uuid}/publish/").status_code == expected


def test_drafts_are_never_exposed_to_anonymous_visitors(mpox):
    PublicNotice.objects.create(kind=NoticeKind.ALERT, title="Brouillon", summary="x")
    anonymous = APIClient()
    assert anonymous.get("/api/v1/diseases/").status_code == 401  # référentiel complet
    assert anonymous.get("/api/v1/portal/notices/").status_code == 401  # annonces en brouillon
    assert anonymous.get("/api/v1/public/diseases/").data == []
    assert anonymous.get("/api/v1/public/diseases/mpox/").status_code == 404
    assert anonymous.get("/api/v1/public/notices/").data == []
    # Le questionnaire n'expose que des libellés de questions, aucun contenu de fiche
    cfg = anonymous.get("/api/v1/public/registration-config/").data["diseases"][0]
    assert not {"description", "prevention", "traveler_recommendations"} & set(cfg)


def test_seed_keeps_new_diseases_inactive_and_unpublished(roles):
    from django.core.management import call_command

    call_command("seed_reference_data", verbosity=0)
    call_command("seed_reference_data", verbosity=0)  # rejouable
    for code in NEW_DISEASES:
        d = Disease.objects.get(code=code)
        assert (d.is_active, d.is_published) == (False, False)
    assert not Disease.objects.filter(is_published=True).exists()
