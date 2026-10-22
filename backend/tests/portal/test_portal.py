"""Portail public multimaladies : catalogue, publication, annonces, parcours voyageur."""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, RoleAssignment, RoleCode
from apps.diseases.catalog import NEW_DISEASES, sync_disease_catalog
from apps.diseases.models import Disease, RiskFactor, Symptom
from apps.geo.models import Country
from apps.geo.services import record_risk_assessment
from apps.portal.models import NoticeKind, NoticeStatus, PublicNotice
from apps.portal.services import apply_screenings, publish_disease, publish_notice
from apps.quarantine.models import QuarantineRecord
from apps.travelers.models import Traveler, TravelHistoryEntry

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


def test_registration_config_lists_only_active_diseases(catalog):
    data = APIClient().get("/api/v1/public/registration-config/").data
    assert data["ebola_questionnaire"] is True
    codes = [d["code"] for d in data["diseases"]]
    assert codes == ["MPOX"]  # Dengue, rougeole, méningite… inactives par défaut
    assert data["diseases"][0]["exposures"][0]["code"] == "contact_lesions"
    assert data["diseases"][0]["followup_days"] == 21


def test_screening_opens_one_followup_per_disease_for_the_same_traveler(traveler, mpox):
    opened = apply_screenings(
        traveler,
        [
            {"disease": "MPOX", "exposures": ["contact_lesions", "inconnu"], "symptoms": []},
        ],
    )
    assert [o["disease_code"] for o in opened] == ["MPOX"]
    case = QuarantineRecord.objects.get(traveler=traveler, disease=mpox)
    action = case.actions.get()
    assert action.metadata["exposures"] == ["contact_lesions"]  # code inconnu ignoré

    # Rejouer ne crée ni doublon de suivi ni doublon d'identité
    apply_screenings(traveler, [{"disease": "MPOX", "symptoms": ["rash"]}])
    assert QuarantineRecord.objects.filter(traveler=traveler, disease=mpox).count() == 1
    assert Traveler.objects.count() == 1


def test_screening_without_exposure_nor_risk_country_opens_nothing(traveler, mpox):
    assert apply_screenings(traveler, [{"disease": "MPOX"}]) == []
    assert not QuarantineRecord.objects.filter(traveler=traveler).exists()


def test_stay_in_a_risk_country_opens_followup_without_answers(traveler, mpox):
    cd = Country.objects.get(code="CD")
    TravelHistoryEntry.objects.create(traveler=traveler, role="origin", country=cd)
    record_risk_assessment(
        country=cd,
        disease=mpox,
        risk_level="moderate",
        justification="j",
        source_reference="Bulletin OMS",
    )
    opened = apply_screenings(traveler, [])
    assert opened[0]["reasons"] == ["séjour/transit : CD"]


def test_inactive_disease_is_never_screened(traveler, catalog):
    apply_screenings(traveler, [{"disease": "DENGUE", "exposures": ["dengue_area_stay"]}])
    assert not QuarantineRecord.objects.filter(traveler=traveler).exists()


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


def test_public_registration_with_several_diseases(pass_keys, entry_point, mpox):
    cache.clear()
    payload = {
        "voyage": {"arrival_date": NOW.date().isoformat(), "entry_point_code": "ABJ"},
        "identite": {"last_name": "KONE", "first_name": "Ali", "gender": "M"},
        "historique": [{"role": "origin", "country_code": "GH"}],
        "confinement": {"city": "Abidjan"},
        "exposure": {},
        "symptoms": {},
        "declaration": {"truthful_declaration": True},
        "screenings": [{"disease": "MPOX", "symptoms": ["rash"]}],
    }
    resp = APIClient().post("/api/v1/ebola/public/register/", payload, format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["pass"]["qr_token"]  # pass QR signé toujours délivré
    assert [f["disease_code"] for f in resp.data["followups"]] == ["MPOX"]

    traveler = Traveler.objects.get(public_id=resp.data["traveler"]["public_id"])
    assert sorted(traveler.quarantines.values_list("disease__code", flat=True)) == [
        "EBOLA",
        "MPOX",
    ]
    declaration = traveler.ebola_investigations.get().declaration
    assert declaration.extra["screenings"][0]["disease"] == "MPOX"

    # Le pass public liste un suivi par maladie pour la même identité
    pass_data = APIClient().get(f"/api/v1/ebola/public/pass/{traveler.public_id}/").data
    assert sorted(f["disease_name"] for f in pass_data["followups"]) == [
        "Maladie à virus Ebola",
        "Mpox (variole simienne)",
    ]
