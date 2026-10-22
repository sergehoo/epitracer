"""Référentiel pays : sous-région ouest-africaine, codes ISO, migration idempotente."""

import importlib
from collections import Counter

import pytest
from django.apps import apps as django_apps

from apps.geo.models import Country, CountryRiskAssessment
from apps.geo.referential import REFERENCE_COUNTRIES, WEST_AFRICA_CODES, sync_reference_countries

pytestmark = pytest.mark.django_db

WEST_AFRICA_EXPECTED = {
    "CI": "CIV",
    "GH": "GHA",
    "TG": "TGO",
    "BJ": "BEN",
    "BF": "BFA",
    "ML": "MLI",
    "NE": "NER",
    "NG": "NGA",
    "GN": "GIN",
    "GW": "GNB",
    "LR": "LBR",
    "SL": "SLE",
    "SN": "SEN",
    "GM": "GMB",
    "CV": "CPV",
    "MR": "MRT",
}

migration_0004 = importlib.import_module("apps.geo.migrations.0004_seed_country_referential")


def test_migration_adds_the_16_west_african_countries_with_iso_codes():
    assert set(WEST_AFRICA_CODES) == set(WEST_AFRICA_EXPECTED)
    for code2, code3 in WEST_AFRICA_EXPECTED.items():
        country = Country.objects.get(code=code2)
        assert country.code3 == code3
        assert country.is_monitored is True


def test_congo_is_kept_in_the_referential():
    assert Country.objects.get(code="CD").code3 == "COD"
    assert Country.objects.get(code="CG").code3 == "COG"


def test_new_countries_are_not_classified_at_risk_automatically():
    west_africa = Country.objects.filter(code__in=WEST_AFRICA_CODES)
    assert set(west_africa.values_list("risk_level", flat=True)) == {"normal"}
    assert not CountryRiskAssessment.objects.filter(country__in=west_africa).exists()


def test_iso_codes_have_no_duplicates():
    codes2 = Counter(Country.all_objects.values_list("code", flat=True))
    codes3 = Counter(c for c in Country.all_objects.values_list("code3", flat=True) if c)
    assert max(codes2.values()) == 1
    assert max(codes3.values()) == 1


def test_sync_is_idempotent():
    before = Country.all_objects.count()
    assert sync_reference_countries(Country) == {"created": 0, "updated": 0}
    assert sync_reference_countries(Country) == {"created": 0, "updated": 0}
    assert Country.all_objects.count() == before


def test_sync_never_overwrites_existing_values():
    Country.objects.filter(code="GH").update(name="Ghana (saisie admin)", is_monitored=False)
    sync_reference_countries(Country)
    gh = Country.objects.get(code="GH")
    assert gh.name == "Ghana (saisie admin)"
    assert gh.is_monitored is False


def test_sync_matches_on_iso3_and_soft_deleted_rows():
    # Ligne existante saisie avec un ISO-3 correct mais un ISO-2 différent : pas de doublon.
    Country.all_objects.filter(code="NE").delete()
    Country.objects.create(code="XN", code3="NER", name="Niger")
    # Ligne supprimée logiquement : retrouvée, pas recréée (sinon violation d'unicité).
    Country.objects.get(code="TG").delete()

    sync_reference_countries(Country)

    assert Country.all_objects.filter(code3="NER").count() == 1
    assert Country.all_objects.filter(code="TG").count() == 1
    assert len(REFERENCE_COUNTRIES) == len({c[0] for c in REFERENCE_COUNTRIES})


def test_migration_turns_legacy_levels_into_dated_assessments(ebola_disease):
    # État « avant migration » : ancienne échelle (red) + liste de maladies.
    CountryRiskAssessment.objects.filter(country__code="CD").delete()
    Country.objects.filter(code="CD").update(risk_level="red", risk_for_diseases=["EBOLA", "XYZ"])
    count_before = Country.all_objects.count()

    migration_0004.forwards(django_apps, None)
    migration_0004.forwards(django_apps, None)  # rejouée : aucun effet supplémentaire

    cd = Country.objects.get(code="CD")
    assert cd.risk_level == "critical"
    assert cd.is_monitored is True
    assessments = CountryRiskAssessment.objects.filter(country=cd)
    assert assessments.count() == 1
    a = assessments.get()
    assert (a.disease, a.risk_level) == (ebola_disease, "critical")
    assert a.source_reference == "Référentiel pays antérieur"
    assert "EBOLA, XYZ" in a.justification
    assert Country.all_objects.count() == count_before


def test_migration_maps_low_to_normal():
    Country.objects.filter(code="FR").update(risk_level="low")
    migration_0004.forwards(django_apps, None)
    assert Country.objects.get(code="FR").risk_level == "normal"
    assert not CountryRiskAssessment.objects.filter(country__code="FR").exists()
