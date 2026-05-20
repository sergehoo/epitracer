import pytest
from django.contrib.gis.geos import Point

from apps.accounts.models import Role, RoleAssignment, RoleCode
from apps.diseases.models import Disease, DiseaseSeverity
from apps.geo.models import Country, EntryPoint, EntryPointType
from apps.travelers.models import Traveler


@pytest.fixture
def ebola_disease(db) -> Disease:
    return Disease.objects.create(
        code="EBOLA", name="Maladie à virus Ebola", short_name="Ebola",
        severity=DiseaseSeverity.CRITICAL, color="#dc2626",
        incubation_min_days=2, incubation_max_days=21,
        surveillance_days=21, quarantine_days=21,
        risk_countries=["CD", "UG"],
        requires_quarantine=True, requires_pass=True,
    )


@pytest.fixture
def country_ci(db) -> Country:
    return Country.objects.create(code="CI", name="Côte d'Ivoire", region="Afrique")


@pytest.fixture
def country_cd(db) -> Country:
    return Country.objects.create(code="CD", name="RDC", region="Afrique", risk_level="red")


@pytest.fixture
def entry_point(db, country_ci) -> EntryPoint:
    return EntryPoint.objects.create(
        code="ABJ", name="Aéroport Abidjan",
        type=EntryPointType.AIRPORT, iata_code="ABJ",
        country=country_ci, city="Abidjan",
        location=Point(-3.9263, 5.2616, srid=4326),
    )


@pytest.fixture
def traveler(db, country_ci, country_cd, entry_point) -> Traveler:
    return Traveler.objects.create(
        first_name="Aïcha", last_name="DIALLO",
        gender="F",
        nationality=country_ci,
        id_document_number="P123456",
        phone_mobile="+2250708090911",
        email="aicha@example.ci",
        entry_point=entry_point,
        confinement_city="Abidjan",
        confinement_commune="Cocody",
    )


@pytest.fixture
def roles(db):
    for code, label in RoleCode.choices:
        Role.objects.get_or_create(code=code, defaults={"name": label, "is_system": True})


@pytest.fixture
def superadmin(db, django_user_model, roles):
    user = django_user_model.objects.create_user(
        email="admin@example.ci", username="admin@example.ci",
        password="StrongPwd!2026", is_staff=True, is_superuser=True,
    )
    role = Role.objects.get(code=RoleCode.NATIONAL_ADMIN)
    RoleAssignment.objects.create(user=user, role=role, is_active=True)
    return user
