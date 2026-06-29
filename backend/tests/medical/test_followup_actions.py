"""Tests des signaux d'auto-log `FollowUpAction`.

On vérifie :
  - création MedicalSample → action SAMPLE_REQUESTED
  - transition transport_status → SAMPLE_COLLECTED puis SENT_TO_LAB
  - création LabAnalysis → SENT_TO_LAB
  - validation d'un LabAnalysis avec résultat → LAB_RESULT_ADDED
"""
from __future__ import annotations

import pytest

from apps.medical.models import (
    FollowUpAction,
    FollowUpActionType,
    LabAnalysis,
    LabAnalysisResult,
    LabAnalysisStatus,
    MedicalSample,
    SampleTransportStatus,
    SampleType,
)


pytestmark = pytest.mark.django_db


def test_sample_creation_logs_action(active_case, superadmin):
    MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-T001",
        sample_type=SampleType.BLOOD,
        collected_by=superadmin,
        destination_lab="IPCI",
    )
    actions = FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.SAMPLE_REQUESTED,
    )
    assert actions.count() == 1
    assert actions.first().metadata["sample_code"] == "EBO-2026-T001"


def test_sample_collected_transition_logs_action(active_case):
    sample = MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-T002",
        sample_type=SampleType.BLOOD,
    )
    # transition vers COLLECTED
    sample.transport_status = SampleTransportStatus.COLLECTED
    sample.save()

    assert FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.SAMPLE_COLLECTED,
    ).exists()


def test_sample_in_transit_logs_sent_to_lab(active_case):
    sample = MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-T003",
        sample_type=SampleType.BLOOD,
        destination_lab="Pasteur Abidjan",
    )
    sample.transport_status = SampleTransportStatus.IN_TRANSIT
    sample.save()

    sent_actions = FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.SENT_TO_LAB,
    )
    # On en attend AU MOINS UNE provenant du sample. La création d'analyses
    # plus tard pourrait en ajouter — ce qui est OK aussi.
    assert sent_actions.exists()


def test_lab_analysis_creation_logs_action(active_case):
    sample = MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-T004",
        sample_type=SampleType.BLOOD,
    )
    LabAnalysis.objects.create(
        sample=sample,
        lab_name="IPCI",
        test_type="PCR Ebola",
        status=LabAnalysisStatus.PENDING,
    )
    assert FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.SENT_TO_LAB,
        metadata__test_type="PCR Ebola",
    ).exists()


def test_lab_analysis_validation_logs_result_added(active_case, superadmin):
    sample = MedicalSample.objects.create(
        followup_case=active_case,
        sample_code="EBO-2026-T005",
        sample_type=SampleType.BLOOD,
    )
    analysis = LabAnalysis.objects.create(
        sample=sample,
        lab_name="IPCI",
        test_type="PCR Ebola",
        status=LabAnalysisStatus.RECEIVED,
    )
    # transition vers VALIDATED + résultat NÉGATIF → action LAB_RESULT_ADDED
    analysis.status = LabAnalysisStatus.VALIDATED
    analysis.result = LabAnalysisResult.NEGATIVE
    analysis.validated_by = superadmin
    analysis.save()

    actions = FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.LAB_RESULT_ADDED,
    )
    assert actions.count() == 1
    assert actions.first().metadata["result"] == "negative"
