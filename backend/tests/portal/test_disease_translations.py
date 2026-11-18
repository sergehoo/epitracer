"""Fiche maladie publique en anglais (`?lang=en`) : traductions enregistrées en base,
français en repli sans rien masquer, valeurs fixes (niveau, transmission) traduites."""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.diseases.catalog import sync_disease_catalog
from apps.diseases.models import Disease, RiskFactor, Symptom
from apps.portal.models import NoticeKind, NoticeStatus, PublicNotice
from apps.portal.services import publish_disease

pytestmark = pytest.mark.django_db

URL = "/api/v1/public/diseases/{slug}/"

EN = {
    "name": "Ebola virus disease",
    "description": "Severe viral illness.",
    "transmission_details": "Direct contact with blood or body fluids.",
    "prevention": "Wash your hands\nAvoid contact with sick people",
    "traveler_recommendations": "Call 143 if you have a fever",
    "symptoms": {"fever": "Fever", "bleeding": "Unexplained bleeding"},
}


@pytest.fixture
def disease(ebola_disease, superadmin) -> Disease:
    sync_disease_catalog(Disease, Symptom, RiskFactor)
    d = Disease.objects.get(pk=ebola_disease.pk)
    d.slug = d.slug or "ebola"
    d.description = "Maladie virale grave."
    d.transmission_details = "Contact direct avec le sang."
    d.prevention = "Se laver les mains\nÉviter tout contact avec les malades"
    d.traveler_recommendations = "Appeler le 143 en cas de fièvre"
    d.transmission_modes = ["contact", "blood"]
    d.public_alert_level = "high"
    d.save()
    d.symptoms.all().delete()
    Symptom.objects.create(disease=d, code="fever", label="Fièvre", order=1)
    Symptom.objects.create(disease=d, code="bleeding", label="Saignements inexpliqués",
                           order=2, is_red_flag=True)
    publish_disease(d, superadmin)
    return d


def _get(disease, lang=None):
    query = f"?lang={lang}" if lang else ""
    resp = APIClient().get(URL.format(slug=disease.slug) + query)
    assert resp.status_code == 200, resp.data
    return resp.data


def test_french_is_unchanged(disease):
    data = _get(disease)
    assert data["name"] == "Maladie à virus Ebola"
    assert data["alert_level_label"] == "Alerte"
    assert data["transmission"] == ["Contact direct/indirect", "Sanguine"]
    assert [s["label"] for s in data["symptoms"]] == ["Fièvre", "Saignements inexpliqués"]
    assert data["untranslated_fields"] == []


def test_english_serves_stored_translations_and_fixed_labels(disease):
    disease.public_translations = {"en": EN}
    disease.save()
    data = _get(disease, "en")
    assert data["name"] == "Ebola virus disease"
    assert data["description"] == "Severe viral illness."
    assert data["transmission_details"] == "Direct contact with blood or body fluids."
    assert data["prevention"] == ["Wash your hands", "Avoid contact with sick people"]
    assert data["traveler_recommendations"] == ["Call 143 if you have a fever"]
    assert [s["label"] for s in data["symptoms"]] == ["Fever", "Unexplained bleeding"]
    assert data["symptoms"][1]["is_red_flag"] is True
    assert data["alert_level_label"] == "Alert"
    assert data["transmission"] == ["Direct/indirect contact", "Blood-borne"]
    assert data["untranslated_fields"] == []


def test_missing_translation_falls_back_to_french_without_hiding_anything(disease):
    disease.public_translations = {
        "en": {"name": "Ebola virus disease", "symptoms": {"fever": "Fever"}},
    }
    disease.save()
    data = _get(disease, "en")
    assert data["name"] == "Ebola virus disease"
    assert data["description"] == "Maladie virale grave."  # repli français
    assert data["prevention"] == ["Se laver les mains", "Éviter tout contact avec les malades"]
    assert [s["label"] for s in data["symptoms"]] == ["Fever", "Saignements inexpliqués"]
    assert set(data["untranslated_fields"]) == {
        "description", "transmission_details", "prevention", "traveler_recommendations", "symptoms",
    }


def test_no_english_translation_at_all(disease):
    data = _get(disease, "en")
    assert data["name"] == "Maladie à virus Ebola"
    assert "name" in data["untranslated_fields"]
    assert data["alert_level_label"] == "Alert"  # valeurs fixes toujours traduites


def test_notices_of_the_fact_sheet_follow_the_language(disease):
    disease.public_translations = {"en": {"name": "Ebola virus disease"}}
    disease.save()
    PublicNotice.objects.create(
        kind=NoticeKind.ALERT, title="Alerte Ebola", summary="Résumé", disease=disease,
        alert_level="critical", status=NoticeStatus.PUBLISHED,
        translations={"en": {"title": "Ebola alert"}},
    )
    notice = _get(disease, "en")["notices"][0]
    assert notice["title"] == "Ebola alert"
    assert notice["summary"] == "Résumé"  # repli français
    assert notice["alert_level_label"] == "Health emergency"
    assert notice["disease"]["name"] == "Ebola virus disease"
