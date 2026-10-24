"""Qualification sanitaire multimaladies, revue humaine et pass découplé d'Ebola."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, RoleAssignment, RoleCode
from apps.diseases.models import Disease, RiskFactor, Symptom
from apps.ebola.models import EbolaInvestigation
from apps.geo.models import Country
from apps.geo.services import record_risk_assessment
from apps.health_pass.models import HealthPass
from apps.health_pass.services import issue_pass, verify_pass
from apps.medical.models import DiseaseFollowupProtocol, HealthScreening
from apps.medical.screening import (
    DEFAULT_SCREENING_RULES,
    apply_screenings,
    confirm_screening,
    dismiss_screening,
    qualify,
)
from apps.quarantine.models import QuarantineRecord
from apps.surveillance.models import HealthAlert
from apps.travelers.models import Traveler, TravelHistoryEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def cholera(db) -> Disease:
    d = Disease.objects.create(code="CHOLERA", name="Choléra", surveillance_days=5)
    for order, (code, label, red) in enumerate(
        [
            ("watery_diarrhea", "Diarrhée aqueuse", False),
            ("vomiting", "Vomissements", False),
            ("dehydration", "Déshydratation", True),
        ]
    ):
        Symptom.objects.create(disease=d, code=code, label=label, order=order, is_red_flag=red)
    RiskFactor.objects.create(disease=d, code="unsafe_water", label="Eau non traitée")
    RiskFactor.objects.create(disease=d, code="contact_case", label="Contact avec un malade")
    return d


# ---------------------------------------------------------------- règles pures


def _q(**kw):
    base = {
        "rules": DEFAULT_SCREENING_RULES,
        "exposures": [],
        "symptoms": [],
        "critical": set(),
        "risk_countries": [],
    }
    return qualify(**{**base, **kw})


def test_isolated_symptom_never_opens_a_followup():
    q = _q(symptoms=["vomiting"])
    assert (q.decision, q.needs_review) == ("isolated_symptom", False)


def test_several_symptoms_without_exposure_require_human_review():
    q = _q(symptoms=["vomiting", "watery_diarrhea"])
    assert (q.decision, q.needs_review, q.severity) == ("review", True, "medium")


def test_critical_symptom_requires_urgent_review():
    q = _q(symptoms=["dehydration"], critical={"dehydration"})
    assert (q.decision, q.severity) == ("review", "high")


def test_exposure_or_risk_itinerary_opens_followup():
    assert _q(exposures=["unsafe_water"]).decision == "followup"
    assert _q(risk_countries=["CD"]).decision == "followup"
    exposed_and_sick = _q(exposures=["unsafe_water"], symptoms=["vomiting"])
    assert (exposed_and_sick.decision, exposed_and_sick.needs_review) == ("followup", True)


def test_protocol_rules_override_defaults():
    strict = {**DEFAULT_SCREENING_RULES, "review_min_symptoms": 1, "followup_on_exposure": False}
    assert _q(rules=strict, symptoms=["vomiting"]).decision == "review"
    # Exposition sans ouverture automatique : un agent décide
    assert _q(rules=strict, exposures=["unsafe_water"]).decision == "review"


# ------------------------------------------------------------- application


def test_common_symptoms_section_is_mapped_without_asking_twice(traveler, cholera):
    """« Diarrhée/vomissements » coché dans le tronc commun compte pour le choléra."""
    results = apply_screenings(traveler, [], common_symptoms={"diarrhea_nausea_vomiting": True})
    assert results[0]["decision"] == "review"
    screening = HealthScreening.objects.get()
    assert screening.answers["symptoms"] == ["vomiting", "watery_diarrhea"]
    assert screening.review_status == "pending"
    assert not QuarantineRecord.objects.exists()  # pas de suivi sans décision humaine
    alert = HealthAlert.objects.get(code="screening_review")
    assert alert.disease == cholera


def test_isolated_symptom_is_traced_but_opens_nothing(traveler, cholera):
    results = apply_screenings(traveler, [], symptom_codes=["vomiting"])
    assert results[0]["decision"] == "isolated_symptom"
    assert HealthScreening.objects.get().review_status == "not_required"
    assert not QuarantineRecord.objects.exists()
    assert not HealthAlert.objects.exists()


def test_protocol_screening_rules_are_applied(traveler, cholera):
    DiseaseFollowupProtocol.objects.create(
        disease=cholera,
        duration_days=7,
        screening_rules={"review_min_symptoms": 1},
    )
    results = apply_screenings(traveler, [], symptom_codes=["vomiting"])
    assert results[0]["decision"] == "review"


def test_risk_itinerary_opens_followup_with_protocol_duration(traveler, cholera):
    DiseaseFollowupProtocol.objects.create(disease=cholera, duration_days=7)
    gh = Country.objects.get(code="GH")
    TravelHistoryEntry.objects.create(traveler=traveler, role="transit", country=gh)
    record_risk_assessment(
        country=gh,
        disease=cholera,
        risk_level="moderate",
        justification="Épidémie déclarée",
        source_reference="Bulletin OMS",
    )
    results = apply_screenings(traveler, [])
    assert results[0]["decision"] == "followup"
    case = QuarantineRecord.objects.get(traveler=traveler, disease=cholera)
    assert (case.expected_end_on - case.started_on).days == 7


def test_one_traveler_several_independent_followups(traveler, cholera, ebola_disease):
    mpox = Disease.objects.create(code="MPOX", name="Mpox", surveillance_days=21)
    RiskFactor.objects.create(disease=mpox, code="contact_lesions", label="Contact lésions")
    apply_screenings(
        traveler,
        [
            {"disease": "CHOLERA", "exposures": ["unsafe_water"]},
            {"disease": "MPOX", "exposures": ["contact_lesions"]},
        ],
    )
    # Rejouer ne duplique ni le suivi ni l'identité
    apply_screenings(traveler, [{"disease": "MPOX", "exposures": ["contact_lesions"]}])
    codes = sorted(traveler.quarantines.values_list("disease__code", flat=True))
    assert codes == ["CHOLERA", "MPOX"]
    assert Traveler.objects.count() == 1


# --------------------------------------------------------------- revue humaine


@pytest.fixture
def pending_screening(traveler, cholera):
    apply_screenings(traveler, [], symptom_codes=["vomiting", "watery_diarrhea"])
    return HealthScreening.objects.get(review_status="pending")


def test_confirm_opens_followup(pending_screening, superadmin):
    confirm_screening(pending_screening, user=superadmin, note="Rappel effectué")
    pending_screening.refresh_from_db()
    assert pending_screening.review_status == "confirmed"
    assert pending_screening.followup_case.disease.code == "CHOLERA"
    assert pending_screening.followup_case.actions.filter(action_type="screening").exists()


def test_dismiss_requires_a_reason(pending_screening, superadmin):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        dismiss_screening(pending_screening, user=superadmin, note=" ")
    dismiss_screening(pending_screening, user=superadmin, note="Gastro-entérite connue")
    assert not QuarantineRecord.objects.exists()


def test_review_api_permissions(pending_screening, superadmin, django_user_model, roles):
    observer = django_user_model.objects.create_user(
        email="obs@example.ci",
        username="obs@example.ci",
        password="StrongPwd!2026",
    )
    RoleAssignment.objects.create(user=observer, role=Role.objects.get(code=RoleCode.OBSERVER))
    obs = APIClient()
    obs.force_authenticate(user=observer)
    assert obs.get("/api/v1/admin/screenings/").status_code == 403

    admin = APIClient()
    admin.force_authenticate(user=superadmin)
    rows = admin.get("/api/v1/admin/screenings/?review_status=pending").data
    rows = rows.get("results", rows)
    assert [r["uuid"] for r in rows] == [str(pending_screening.uuid)]
    resp = admin.post(
        f"/api/v1/admin/screenings/{pending_screening.uuid}/confirm/", {}, format="json"
    )
    assert resp.status_code == 200, resp.data
    assert resp.data["review_status"] == "confirmed"
    again = admin.post(f"/api/v1/admin/screenings/{pending_screening.uuid}/dismiss/", {"note": "x"})
    assert again.status_code == 400


# ------------------------------------------------------------ pass découplé


def _register(**overrides):
    payload = {
        "voyage": {"arrival_date": timezone.now().date().isoformat(), "entry_point_code": "ABJ"},
        "identite": {"last_name": "BAMBA", "first_name": "Inès", "gender": "F"},
        "historique": [{"role": "origin", "country_code": "FR", "city": "Paris"}],
        "confinement": {"city": "Abidjan"},
        "exposure": {},
        "symptoms": {},
        "declaration": {"truthful_declaration": True},
        **overrides,
    }
    return APIClient().post("/api/v1/ebola/public/register/", payload, format="json")


def test_pass_is_issued_without_any_active_disease(pass_keys, entry_point):
    """Aucune maladie active (Ebola absente) : l'enregistrement délivre quand même le pass."""
    resp = _register()
    assert resp.status_code == 201, resp.data
    assert resp.data["investigation"] is None
    assert not EbolaInvestigation.objects.exists()
    hp = HealthPass.objects.get(pass_number=resp.data["pass"]["pass_number"])
    assert hp.disease is None and hp.payload["dis"] is None
    assert hp.investigation_ref == resp.data["traveler"]["public_id"]
    assert verify_pass(resp.data["pass"]["qr_token"])["is_valid"] is True


def test_inactive_ebola_neither_investigates_nor_blocks_the_pass(
    pass_keys, entry_point, ebola_disease
):
    ebola_disease.is_active = False
    ebola_disease.save()
    resp = _register(exposure={"visited_ebola_zone": True})
    assert resp.status_code == 201, resp.data
    assert not EbolaInvestigation.objects.exists()
    assert resp.data["pass"]["qr_token"]


def test_pass_shows_moderate_when_a_followup_is_opened(pass_keys, entry_point, cholera):
    resp = _register(screenings=[{"disease": "CHOLERA", "exposures": ["unsafe_water"]}])
    assert resp.status_code == 201, resp.data
    hp = HealthPass.objects.get(pass_number=resp.data["pass"]["pass_number"])
    assert hp.risk_level == "moderate"
    assert verify_pass(resp.data["pass"]["qr_token"])["followed_diseases"] == ["Choléra"]


def test_existing_ebola_bound_pass_still_verifies(pass_keys, traveler, ebola_disease):
    """Pass émis avant le découplage (dis=EBOLA) : signature et vérification inchangées."""
    from apps.ebola.public_views import _safe_qr_token

    legacy = issue_pass(
        traveler=traveler,
        disease=ebola_disease,
        risk_level="low",
        investigation_ref="EBO-2026-000001",
    )
    assert legacy.payload["dis"] == "EBOLA"
    result = verify_pass(_safe_qr_token(legacy))
    assert result["is_valid"] is True
