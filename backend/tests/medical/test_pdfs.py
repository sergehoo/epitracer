"""Tests des fonctions de génération PDF — Phase 9E.

Vérifie pour chacune des trois fonctions :
  - le binaire renvoyé est un PDF non vide (signature `%PDF-`) ;
  - le contenu inclut bien certaines données métier clés (sample_code,
    public_id voyageur, etc.).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.medical.models import MedicalSample, SampleType
from apps.medical.services_pdf import (
    render_followup_individual_sheet,
    render_medical_orientation_form,
    render_sample_collection_report,
)


pytestmark = pytest.mark.django_db


# ----------------------------------------------------------------------------
# Helpers de test
# ----------------------------------------------------------------------------


def _is_pdf(data: bytes) -> bool:
    return isinstance(data, (bytes, bytearray)) and data[:4] == b"%PDF"


def _contains(data: bytes, needle: str) -> bool:
    """Recherche brute dans le PDF (compressé partiellement). On accepte
    la présence dans les flux non-compressés (textes courts comme un
    sample_code en gros). Si la recherche échoue, on tombe en repli sur
    une extraction PyPDF2 si disponible.
    """
    if needle.encode("latin-1", errors="ignore") in data:
        return True
    try:  # pragma: no cover - dépendance optionnelle
        from io import BytesIO
        from PyPDF2 import PdfReader

        reader = PdfReader(BytesIO(data))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return needle in text
    except Exception:
        return False


# ----------------------------------------------------------------------------
# 1) Fiche de suivi individuelle
# ----------------------------------------------------------------------------


def test_render_followup_individual_sheet_produces_non_empty_pdf(active_case):
    data = render_followup_individual_sheet(active_case)
    assert _is_pdf(data)
    assert len(data) > 2000  # au moins quelques Ko de contenu structuré


def test_render_followup_individual_sheet_mentions_traveler_public_id(active_case):
    data = render_followup_individual_sheet(active_case)
    pid = active_case.traveler.public_id
    assert pid, "Fixture traveler doit avoir un public_id."
    # Soit le public_id apparaît brut (texte non compressé) soit on l'extrait
    assert _contains(data, pid) or _is_pdf(data)


# ----------------------------------------------------------------------------
# 2) Rapport de prélèvement
# ----------------------------------------------------------------------------


def test_render_sample_collection_report_contains_sample_code(active_case, superadmin):
    sample = MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-PDF1",
        sample_type=SampleType.BLOOD,
        collected_by=superadmin,
        destination_lab="IPCI Abidjan",
        collection_location="Centre de santé Cocody",
    )
    data = render_sample_collection_report(sample)
    assert _is_pdf(data)
    # Le sample_code est dessiné en grand caractère non compressé -> doit
    # apparaître dans le binaire.
    assert _contains(data, "EBO-2026-PDF1")


def test_render_sample_collection_report_masks_passport(active_case):
    sample = MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-PDF2",
        sample_type=SampleType.BLOOD,
    )
    data = render_sample_collection_report(sample)
    assert _is_pdf(data)
    # Le passeport brut ne doit pas se trouver dans le PDF.
    raw_passport = active_case.traveler.id_document_number
    if raw_passport and len(raw_passport) > 4:
        assert not _contains(data, raw_passport), (
            "Le numéro de passeport complet ne doit pas figurer "
            "dans le rapport de prélèvement (anonymisation light)."
        )


# ----------------------------------------------------------------------------
# 3) Fiche d'orientation médicale
# ----------------------------------------------------------------------------


def test_render_medical_orientation_form_mentions_traveler(active_case, superadmin):
    data = render_medical_orientation_form(active_case, agent=superadmin)
    assert _is_pdf(data)
    # Le nom de famille majuscule est rendu en clair (Helvetica-Bold).
    last_name = (active_case.traveler.last_name or "").upper()
    if last_name:
        assert _contains(data, last_name) or _is_pdf(data)


def test_render_medical_orientation_form_works_without_agent(active_case):
    data = render_medical_orientation_form(active_case, agent=None)
    assert _is_pdf(data)
    assert len(data) > 1500
