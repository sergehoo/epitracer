"""Tests modèles `medical` — création basique + contraintes."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.db import IntegrityError

from apps.medical.models import (
    CaseClassification,
    CaseClassificationCode,
    FollowUpAction,
    FollowUpActionType,
    LabAnalysis,
    LabAnalysisResult,
    LabAnalysisStatus,
    MedicalSample,
    MedicalSymptomReport,
    SampleTransportStatus,
    SampleType,
    SymptomSeverity,
    SymptomSource,
)


pytestmark = pytest.mark.django_db


def test_disease_followup_protocol_create(ebola_protocol):
    assert ebola_protocol.duration_days == 21
    assert ebola_protocol.require_geolocation is True
    assert "fever" in ebola_protocol.critical_symptoms
    assert ebola_protocol.escalation_rules["missed_checkins"] == 2


def test_symptom_report_create(active_case, superadmin):
    report = MedicalSymptomReport.objects.create(
        followup_case=active_case,
        symptom_code="fever",
        symptom_label="Fièvre",
        severity=SymptomSeverity.MODERATE,
        onset_date=date.today(),
        reported_by_user=superadmin,
        source=SymptomSource.CHECKIN,
        is_critical=True,
    )
    assert report.followup_case == active_case
    assert report.is_critical is True

    # Le signal post_save doit créer une FollowUpAction SYMPTOM_DECLARED.
    actions = FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.SYMPTOM_DECLARED,
    )
    assert actions.exists()
    assert actions.first().metadata["symptom_code"] == "fever"


def test_medical_sample_unique_code(active_case):
    MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-0001",
        sample_type=SampleType.BLOOD,
        transport_status=SampleTransportStatus.REQUESTED,
    )
    with pytest.raises(IntegrityError):
        MedicalSample.objects.create(
            followup_case=active_case,
            sample_code="EBO-2026-0001",
            sample_type=SampleType.SALIVA,
        )


def test_lab_analysis_create(active_case):
    sample = MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-0002",
        sample_type=SampleType.BLOOD,
        transport_status=SampleTransportStatus.RECEIVED,
    )
    analysis = LabAnalysis.objects.create(
        sample=sample,
        lab_name="IPCI",
        test_type="PCR Ebola",
        status=LabAnalysisStatus.PENDING,
        result=LabAnalysisResult.EMPTY,
    )
    assert analysis.sample == sample
    assert analysis.result == ""  # EMPTY


def test_case_classification_creates_action_and_updates_cache(active_case, superadmin):
    cc = CaseClassification.objects.create(
        followup_case=active_case,
        classification=CaseClassificationCode.SUSPECT,
        reason="2 symptômes critiques en 24h",
        classified_by=superadmin,
        is_current=True,
    )
    # Action auto via signal
    assert FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.CASE_CLASSIFIED,
    ).exists()

    # Cache de classification mis à jour sur le QuarantineRecord
    active_case.refresh_from_db()
    assert active_case.current_classification == CaseClassificationCode.SUSPECT


def test_quarantine_record_new_fields(active_case, superadmin):
    """Les nouveaux champs sont bien présents et persistés."""
    active_case.assigned_team = "Équipe Abidjan-Sud"
    active_case.assigned_agent = superadmin
    active_case.closure_reason = "auto_completed"
    active_case.save()

    active_case.refresh_from_db()
    assert active_case.assigned_team == "Équipe Abidjan-Sud"
    assert active_case.assigned_agent_id == superadmin.id
    assert active_case.closure_reason == "auto_completed"


def test_daily_check_new_fields(active_case, superadmin):
    """DailyCheck.status + nouveaux champs."""
    from apps.quarantine.models import DailyCheck, DailyCheckStatus

    check = DailyCheck.objects.create(
        quarantine=active_case,
        day_index=3,
        check_date=date.today(),
        has_symptoms=False,
        status=DailyCheckStatus.VISIT_SCHEDULED,
        agent_responsible=superadmin,
        decision="Visite programmée pour demain",
        location_shared=True,
        notification_sent=True,
    )
    check.refresh_from_db()
    assert check.status == DailyCheckStatus.VISIT_SCHEDULED
    assert check.location_shared is True
    assert check.notification_sent is True
