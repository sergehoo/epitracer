"""Tests du moteur de scoring Ebola."""
import pytest
from django.utils import timezone

from apps.ebola.models import EbolaExposureAssessment, EbolaInvestigation, EbolaSymptomReport
from apps.ebola.services import apply_risk_outcome, compute_ebola_risk_score


pytestmark = pytest.mark.django_db


def _make_investigation(traveler, entry_point):
    return EbolaInvestigation.objects.create(traveler=traveler, entry_point=entry_point)


def test_low_risk_default(traveler, entry_point, ebola_disease):
    inv = _make_investigation(traveler, entry_point)
    score, level = compute_ebola_risk_score(inv)
    assert score == 0
    assert level == "low"


def test_high_risk_with_exposure_and_symptoms(traveler, entry_point, ebola_disease):
    inv = _make_investigation(traveler, entry_point)
    EbolaExposureAssessment.objects.create(
        investigation=inv,
        visited_outbreak_country=True,        # +25
        contact_with_confirmed_case=True,     # +35
        attended_funerals=True,               # +20
    )
    EbolaSymptomReport.objects.create(
        investigation=inv, reported_at=timezone.now(),
        temperature_celsius=39.0,             # +15
        fever=True, severe_headache=True, vomiting=True,  # systémiques (3) +15
    )
    score, level = compute_ebola_risk_score(inv)
    assert score >= 80
    assert level == "critical"


def test_red_flag_bleeding_triggers_critical(traveler, entry_point, ebola_disease):
    inv = _make_investigation(traveler, entry_point)
    EbolaExposureAssessment.objects.create(
        investigation=inv, visited_outbreak_country=True,
    )
    EbolaSymptomReport.objects.create(
        investigation=inv, reported_at=timezone.now(),
        unexplained_bleeding=True,            # +30
    )
    score, level = compute_ebola_risk_score(inv)
    assert score >= 55
    assert level in {"high", "critical"}


def test_apply_risk_outcome_sets_workflow(traveler, entry_point, ebola_disease):
    inv = _make_investigation(traveler, entry_point)
    EbolaExposureAssessment.objects.create(
        investigation=inv,
        visited_outbreak_country=True, contact_with_confirmed_case=True,
    )
    apply_risk_outcome(inv)
    inv.refresh_from_db()
    assert inv.risk_score > 0
    assert inv.surveillance_start is not None
    assert inv.surveillance_end is not None
    assert inv.status in {"surveillance", "quarantine", "suspect"}
