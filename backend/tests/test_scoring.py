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
        visited_ebola_zone=True,                    # +25
        contact_with_case=True,                     # +35
        attended_funeral_or_touched_corpse=True,    # +20
    )
    EbolaSymptomReport.objects.create(
        investigation=inv, reported_at=timezone.now(),
        temperature_celsius=39.0,                   # fièvre élevée +10
        fever=True,                                 # +10
        severe_headache=True,                       # +3
        diarrhea_nausea_vomiting=True,              # +5
    )
    score, level = compute_ebola_risk_score(inv)
    assert score == 100  # 108 plafonné à 100
    assert level == "critical"


def test_red_flag_bleeding_triggers_high(traveler, entry_point, ebola_disease):
    inv = _make_investigation(traveler, entry_point)
    EbolaExposureAssessment.objects.create(investigation=inv, visited_ebola_zone=True)  # +25
    EbolaSymptomReport.objects.create(
        investigation=inv, reported_at=timezone.now(),
        unexplained_bleeding=True,                  # +30
    )
    score, level = compute_ebola_risk_score(inv)
    assert score == 55
    assert level == "high"


def test_apply_risk_outcome_sets_workflow(traveler, entry_point, ebola_disease):
    inv = _make_investigation(traveler, entry_point)
    EbolaExposureAssessment.objects.create(
        investigation=inv, visited_ebola_zone=True, contact_with_case=True,  # 60 → critique
    )
    apply_risk_outcome(inv)
    inv.refresh_from_db()
    traveler.refresh_from_db()
    assert (inv.risk_score, inv.risk_level, inv.status) == (60, "critical", "suspect")
    assert inv.surveillance_start is not None
    assert inv.surveillance_end is not None
    assert traveler.current_health_status == "suspect"
    assert traveler.quarantines.filter(disease=ebola_disease).count() == 1
