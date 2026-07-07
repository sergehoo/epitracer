"""Tests d'API DRF du module medical (Phase 9B).

Couvre :
- détail d'un suivi + journalisation DataAccessLog
- création de prélèvement + auto-génération du sample_code
- classification : transition is_current
- contrôle des permissions sur /lab-results/
- endpoint timeline
- endpoint audit avec reason obligatoire
- endpoint public /status/ ne révèle pas de PII
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.companion.models import DataAccessLog
from apps.medical.models import (
    CaseClassification,
    FollowUpAction,
    MedicalSample,
)


@pytest.fixture
def auth_client(superadmin):
    client = APIClient()
    client.force_authenticate(user=superadmin)
    return client


@pytest.mark.django_db
def test_followup_detail_returns_case_and_logs_access(
    auth_client, active_case, ebola_protocol, traveler,
):
    url = f"/api/v1/admin/followups/{traveler.public_id}/"
    resp = auth_client.get(url)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["public_id"] == traveler.public_id
    # DataAccessLog créé
    assert DataAccessLog.objects.filter(
        traveler=traveler, resource=DataAccessLog.Resource.HEALTH,
    ).exists()


@pytest.mark.django_db
def test_create_sample_auto_generates_code(
    auth_client, active_case, ebola_protocol, traveler,
):
    url = f"/api/v1/admin/followups/{traveler.public_id}/samples/"
    resp = auth_client.post(
        url, {"sample_type": "blood", "destination_lab": "INHP Adjamé"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    sample_code = resp.json()["sample_code"]
    year = date.today().year
    assert sample_code == f"EBOLA-{year}-0001"

    resp2 = auth_client.post(url, {"sample_type": "blood"}, format="json")
    assert resp2.status_code == 201
    assert resp2.json()["sample_code"] == f"EBOLA-{year}-0002"

    assert MedicalSample.objects.filter(followup_case=active_case).count() == 2


@pytest.mark.django_db
def test_classification_transition_marks_current_correctly(
    auth_client, active_case, traveler,
):
    url = f"/api/v1/admin/followups/{traveler.public_id}/classify/"
    r1 = auth_client.post(
        url, {"classification": "suspect", "reason": "Fièvre + retour zone à risque"},
        format="json",
    )
    assert r1.status_code == 201, r1.content
    r2 = auth_client.post(
        url, {"classification": "confirmed", "reason": "PCR positif"},
        format="json",
    )
    assert r2.status_code == 201, r2.content

    classifications = CaseClassification.objects.filter(followup_case=active_case)
    assert classifications.count() == 2
    current = classifications.filter(is_current=True)
    assert current.count() == 1
    assert current.first().classification == "confirmed"


@pytest.mark.django_db
def test_lab_result_forbidden_for_field_agent(
    db, roles, active_case, traveler, django_user_model,
):
    from apps.accounts.models import Role, RoleAssignment, RoleCode

    user = django_user_model.objects.create_user(
        email="agent@example.ci", username="agent@example.ci",
        password="StrongAgent!2026",
    )
    role = Role.objects.get(code=RoleCode.FIELD_AGENT)
    RoleAssignment.objects.create(user=user, role=role, is_active=True)

    client = APIClient()
    client.force_authenticate(user=user)
    url = f"/api/v1/admin/followups/{traveler.public_id}/lab-results/"
    resp = client.post(
        url,
        {"sample_id": 999, "lab_name": "INHP", "test_type": "PCR", "result": "negative"},
        format="json",
    )
    # Field agent : doit être interdit (CanAddLabResult exige LAB ou INHP)
    assert resp.status_code in (403, 401)


@pytest.mark.django_db
def test_timeline_returns_enriched_daily_checks(
    auth_client, active_case, traveler,
):
    from apps.quarantine.models import DailyCheck, DailyCheckStatus

    DailyCheck.objects.create(
        quarantine=active_case,
        day_index=1,
        check_date=date.today() - timedelta(days=2),
        status=DailyCheckStatus.COMPLETED,
        has_symptoms=False,
    )
    url = f"/api/v1/admin/followups/{traveler.public_id}/timeline/"
    resp = auth_client.get(url)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    items = body.get("results", body)
    assert any(d.get("day_index") == 1 for d in items)


@pytest.mark.django_db
def test_audit_requires_reason(auth_client, active_case, traveler):
    url = f"/api/v1/admin/followups/{traveler.public_id}/audit/"
    resp = auth_client.get(url)
    assert resp.status_code == 400

    resp = auth_client.get(url + "?reason=Investigation%20HA-1234")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_audit_includes_actions_and_access(auth_client, active_case, traveler):
    FollowUpAction.objects.create(
        followup_case=active_case, action_type="contacted",
        title="Appel téléphonique",
    )
    DataAccessLog.objects.create(
        traveler=traveler, resource=DataAccessLog.Resource.HEALTH,
        reason="Test", accessed_by_role="INHP",
    )
    url = f"/api/v1/admin/followups/{traveler.public_id}/audit/?reason=audit-test"
    resp = auth_client.get(url)
    assert resp.status_code == 200
    body = resp.json()
    items = body.get("results", body)
    types = {it.get("type") for it in items}
    assert "action" in types
    assert "access" in types


@pytest.mark.django_db
def test_public_status_does_not_reveal_pii(active_case, ebola_protocol, traveler):
    client = APIClient()  # AllowAny
    url = f"/api/v1/public/followup/status/?public_id={traveler.public_id}"
    resp = client.get(url)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    haystack = str(body).lower()

    # Aucune PII en clair
    assert traveler.phone_mobile.lower() not in haystack
    assert traveler.email.lower() not in haystack
    assert "id_document_number" not in body
    assert traveler.id_document_number.lower() not in haystack

    # Mais public_id + maladie sont OK (non-PII)
    assert body["public_id"] == traveler.public_id
    assert "disease_code" in body


@pytest.mark.django_db
def test_followup_actions_creates_action_and_logs(
    auth_client, active_case, traveler,
):
    url = f"/api/v1/admin/followups/{traveler.public_id}/actions/"
    resp = auth_client.post(url, {
        "action_type": "contacted",
        "title": "Appel à domicile",
        "description": "Pas de réponse.",
    }, format="json")
    assert resp.status_code == 201, resp.content
    assert FollowUpAction.objects.filter(
        followup_case=active_case, title="Appel à domicile",
    ).exists()


@pytest.mark.django_db
def test_followup_close_updates_case_status(
    auth_client, active_case, traveler,
):
    url = f"/api/v1/admin/followups/{traveler.public_id}/close/"
    resp = auth_client.post(url, {
        "closure_reason": "manual_close",
        "final_status": "completed",
        "notes": "Suivi terminé sans alerte.",
    }, format="json")
    assert resp.status_code == 200, resp.content
    active_case.refresh_from_db()
    assert active_case.status == "completed"
    assert active_case.closure_reason == "manual_close"


# ============================================================================
# Phase 9F — GET liste paginée + unmask-phone
# ============================================================================


@pytest.mark.django_db
def test_symptoms_get_returns_paginated_list_with_filter(
    auth_client, active_case, ebola_protocol, traveler,
):
    """GET /symptoms/ renvoie les rapports triés -created_at avec filtre is_critical."""
    from apps.medical.models import MedicalSymptomReport, SymptomSource
    from datetime import date

    MedicalSymptomReport.objects.create(
        followup_case=active_case, symptom_code="fever",
        symptom_label="Fièvre", severity="critical",
        onset_date=date.today(), source=SymptomSource.CHECKIN,
        is_critical=True,
    )
    MedicalSymptomReport.objects.create(
        followup_case=active_case, symptom_code="cough",
        symptom_label="Toux", severity="mild",
        onset_date=date.today(), source=SymptomSource.ADMIN,
        is_critical=False,
    )

    url = f"/api/v1/admin/followups/{traveler.public_id}/symptoms/"
    resp = auth_client.get(url)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    results = body.get("results", [])
    assert len(results) == 2

    # Filtre is_critical=true
    resp_crit = auth_client.get(url + "?is_critical=true")
    assert resp_crit.status_code == 200
    body_crit = resp_crit.json()
    assert all(r["is_critical"] for r in body_crit.get("results", []))
    assert len(body_crit.get("results", [])) == 1


@pytest.mark.django_db
def test_samples_get_returns_paginated_list(
    auth_client, active_case, traveler,
):
    """GET /samples/ renvoie la liste paginée + filtre transport_status."""
    from apps.medical.models import MedicalSample, SampleTransportStatus

    MedicalSample.objects.create(
        followup_case=active_case, sample_code="EBOLA-TEST-001",
        sample_type="blood",
        transport_status=SampleTransportStatus.REQUESTED,
    )
    MedicalSample.objects.create(
        followup_case=active_case, sample_code="EBOLA-TEST-002",
        sample_type="blood",
        transport_status=SampleTransportStatus.COLLECTED,
    )

    url = f"/api/v1/admin/followups/{traveler.public_id}/samples/"
    resp = auth_client.get(url)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert len(body.get("results", [])) == 2

    resp_filt = auth_client.get(url + "?transport_status=requested")
    assert resp_filt.status_code == 200
    results = resp_filt.json().get("results", [])
    assert len(results) == 1
    assert results[0]["transport_status"] == "requested"


@pytest.mark.django_db
def test_lab_results_get_returns_paginated_list(
    auth_client, active_case, traveler,
):
    """GET /lab-results/ renvoie les analyses des prélèvements du cas."""
    from apps.medical.models import (
        LabAnalysis, LabAnalysisStatus, MedicalSample,
    )

    sample = MedicalSample.objects.create(
        followup_case=active_case, sample_code="EBOLA-TEST-010",
        sample_type="blood",
    )
    LabAnalysis.objects.create(
        sample=sample, lab_name="INHP", test_type="PCR",
        result="positive", status=LabAnalysisStatus.RESULT_AVAILABLE,
    )

    url = f"/api/v1/admin/followups/{traveler.public_id}/lab-results/"
    resp = auth_client.get(url)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    results = body.get("results", [])
    assert len(results) == 1
    assert results[0]["result"] == "positive"

    # Filtre par result
    resp_neg = auth_client.get(url + "?result=negative")
    assert resp_neg.status_code == 200
    assert len(resp_neg.json().get("results", [])) == 0


@pytest.mark.django_db
def test_unmask_phone_requires_reason_and_creates_log(
    auth_client, active_case, traveler,
):
    """POST /unmask-phone/ exige reason et crée une entrée DataAccessLog."""
    url = f"/api/v1/admin/followups/{traveler.public_id}/unmask-phone/"
    # Sans raison → 400
    resp_400 = auth_client.post(url, {}, format="json")
    assert resp_400.status_code == 400

    # Avec raison → 200 + DataAccessLog créé
    resp = auth_client.post(
        url + "?reason=Investigation%20HA-9999", {}, format="json",
    )
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body.get("phone") == traveler.phone_mobile
    assert body.get("reason") == "Investigation HA-9999"

    # DataAccessLog créé avec préfixe phone_unmask
    logs = DataAccessLog.objects.filter(
        traveler=traveler,
        resource=DataAccessLog.Resource.IDENTITY,
    )
    assert logs.exists()
    assert any("phone_unmask" in log.reason for log in logs)
