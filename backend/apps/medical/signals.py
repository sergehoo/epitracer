"""Signaux Django — auto-log de `FollowUpAction` + automation (Phase 9D).

Phase 9A : on capture les événements clés sur les modèles medical pour
alimenter automatiquement la timeline du cas (FollowUpAction).

Phase 9D : on étend pour déclencher en plus des tâches Celery :
  - MedicalSymptomReport(is_critical=True) → `escalate_critical_symptoms_for_case`
  - LabAnalysis(result="positive") → auto-classification "confirmed" + alerte
  - MedicalSample(transport_status="rejected") → FollowUpAction + alerte

Aucun PII n'est mis en clair dans le champ description / metadata (pas de
téléphone, pas de passeport — uniquement public_id du voyageur).
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import (
    CaseClassification,
    CaseClassificationCode,
    FollowUpAction,
    FollowUpActionStatus,
    FollowUpActionType,
    LabAnalysis,
    LabAnalysisResult,
    LabAnalysisStatus,
    MedicalSample,
    MedicalSymptomReport,
    SampleTransportStatus,
)

logger = logging.getLogger("epidemitracker.medical.signals")


# ---------------------------------------------------------------------------
# MedicalSymptomReport
# ---------------------------------------------------------------------------


@receiver(post_save, sender=MedicalSymptomReport)
def _log_symptom_declared(sender, instance: MedicalSymptomReport, created, **kwargs):
    if not created:
        return
    FollowUpAction.objects.create(
        followup_case=instance.followup_case,
        followup_day=instance.followup_day,
        action_type=FollowUpActionType.SYMPTOM_DECLARED,
        title=f"Symptôme déclaré : {instance.symptom_label or instance.symptom_code}",
        description=(
            f"Sévérité : {instance.severity}. Source : {instance.source}. "
            f"Critique : {'oui' if instance.is_critical else 'non'}."
        ),
        performed_by=instance.reported_by_user,
        status=FollowUpActionStatus.COMPLETED,
        metadata={
            "symptom_code": instance.symptom_code,
            "severity": instance.severity,
            "is_critical": instance.is_critical,
            "source": instance.source,
            "symptom_report_uuid": str(instance.uuid),
            "symptom_report_id": instance.pk,
        },
    )


@receiver(post_save, sender=MedicalSymptomReport)
def _trigger_escalation_on_critical(sender, instance: MedicalSymptomReport, created, **kwargs):
    """Phase 9D — déclenche l'escalade Celery pour les symptômes critiques."""
    if not created or not instance.is_critical:
        return
    try:
        from .tasks import escalate_critical_symptoms_for_case

        escalate_critical_symptoms_for_case.delay(
            instance.followup_case_id,
            reason="critical_symptom",
            symptom_code=instance.symptom_code,
            symptom_report_id=instance.pk,
        )
    except Exception:  # pragma: no cover - dev sync fallback
        try:
            from .tasks import escalate_critical_symptoms_for_case

            escalate_critical_symptoms_for_case.run(
                instance.followup_case_id,
                reason="critical_symptom",
                symptom_code=instance.symptom_code,
                symptom_report_id=instance.pk,
            )
        except Exception:
            logger.exception("Escalade Celery KO pour MedicalSymptomReport=%s", instance.pk)


# ---------------------------------------------------------------------------
# MedicalSample — création + transitions de statut
# ---------------------------------------------------------------------------


@receiver(pre_save, sender=MedicalSample)
def _capture_sample_previous_status(sender, instance: MedicalSample, **kwargs):
    """Stocke le status précédent sur l'instance pour le post_save."""
    if instance.pk:
        try:
            previous = MedicalSample.objects.only("transport_status").get(pk=instance.pk)
            instance._previous_transport_status = previous.transport_status
        except MedicalSample.DoesNotExist:  # pragma: no cover
            instance._previous_transport_status = None
    else:
        instance._previous_transport_status = None


@receiver(post_save, sender=MedicalSample)
def _log_sample_lifecycle(sender, instance: MedicalSample, created, **kwargs):
    previous = getattr(instance, "_previous_transport_status", None)
    if created:
        FollowUpAction.objects.create(
            followup_case=instance.followup_case,
            followup_day=instance.followup_day,
            action_type=FollowUpActionType.SAMPLE_REQUESTED,
            title=f"Prélèvement demandé : {instance.sample_code}",
            description=(
                f"Type : {instance.sample_type}. "
                f"Destination : {instance.destination_lab or 'non précisée'}."
            ),
            performed_by=instance.collected_by,
            status=FollowUpActionStatus.COMPLETED,
            metadata={
                "sample_code": instance.sample_code,
                "sample_type": instance.sample_type,
                "sample_uuid": str(instance.uuid),
            },
        )
        return

    if previous == instance.transport_status:
        return

    if instance.transport_status == SampleTransportStatus.COLLECTED:
        FollowUpAction.objects.create(
            followup_case=instance.followup_case,
            followup_day=instance.followup_day,
            action_type=FollowUpActionType.SAMPLE_COLLECTED,
            title=f"Prélèvement effectué : {instance.sample_code}",
            performed_by=instance.collected_by,
            status=FollowUpActionStatus.COMPLETED,
            metadata={
                "sample_code": instance.sample_code,
                "sample_uuid": str(instance.uuid),
            },
        )
    elif instance.transport_status == SampleTransportStatus.IN_TRANSIT:
        FollowUpAction.objects.create(
            followup_case=instance.followup_case,
            followup_day=instance.followup_day,
            action_type=FollowUpActionType.SENT_TO_LAB,
            title=f"Prélèvement envoyé : {instance.sample_code}",
            description=f"Destination : {instance.destination_lab or 'non précisée'}.",
            performed_by=instance.collected_by,
            status=FollowUpActionStatus.COMPLETED,
            metadata={
                "sample_code": instance.sample_code,
                "sample_uuid": str(instance.uuid),
            },
        )
    elif instance.transport_status == SampleTransportStatus.REJECTED:
        # Phase 9D — alerte + log distincts pour les rejets de prélèvement
        FollowUpAction.objects.create(
            followup_case=instance.followup_case,
            followup_day=instance.followup_day,
            action_type=FollowUpActionType.ALERT_CREATED,
            title=f"Prélèvement rejeté : {instance.sample_code}",
            description=(
                f"Le laboratoire {instance.destination_lab or '(non précisé)'} "
                f"a rejeté le prélèvement. Nouveau prélèvement requis."
            ),
            performed_by=instance.collected_by,
            status=FollowUpActionStatus.COMPLETED,
            metadata={
                "sample_code": instance.sample_code,
                "sample_uuid": str(instance.uuid),
                "kind": "sample_rejected",
            },
        )
        try:
            from apps.surveillance.services import trigger_alert

            trigger_alert(
                code=f"sample-rejected-{instance.uuid}",
                title=f"Prélèvement rejeté : {instance.sample_code}",
                description=(
                    f"Voyageur {instance.followup_case.traveler.public_id} — "
                    f"prélèvement {instance.sample_code} rejeté par le laboratoire."
                ),
                severity="medium",
                disease=instance.followup_case.disease,
                target=instance.followup_case,
                metadata={
                    "sample_code": instance.sample_code,
                    "sample_uuid": str(instance.uuid),
                },
            )
        except Exception:  # pragma: no cover - best-effort
            logger.exception("Alerte sample rejected KO (sample=%s)", instance.pk)


# ---------------------------------------------------------------------------
# LabAnalysis — création + résultat validé
# ---------------------------------------------------------------------------


@receiver(pre_save, sender=LabAnalysis)
def _capture_lab_previous(sender, instance: LabAnalysis, **kwargs):
    if instance.pk:
        try:
            previous = LabAnalysis.objects.only("status", "result").get(pk=instance.pk)
            instance._previous_status = previous.status
            instance._previous_result = previous.result
        except LabAnalysis.DoesNotExist:  # pragma: no cover
            instance._previous_status = None
            instance._previous_result = None
    else:
        instance._previous_status = None
        instance._previous_result = None


@receiver(post_save, sender=LabAnalysis)
def _log_lab_lifecycle(sender, instance: LabAnalysis, created, **kwargs):
    case = instance.sample.followup_case if instance.sample_id else None
    if case is None:
        return

    if created:
        FollowUpAction.objects.create(
            followup_case=case,
            action_type=FollowUpActionType.SENT_TO_LAB,
            title=f"Analyse demandée : {instance.test_type}",
            description=f"Laboratoire : {instance.lab_name}.",
            performed_by=instance.validated_by,
            status=FollowUpActionStatus.COMPLETED,
            metadata={
                "sample_code": instance.sample.sample_code,
                "test_type": instance.test_type,
                "lab_name": instance.lab_name,
                "lab_analysis_uuid": str(instance.uuid),
            },
        )
        return

    previous_status = getattr(instance, "_previous_status", None)
    if instance.status != previous_status and instance.status in (
        LabAnalysisStatus.VALIDATED, LabAnalysisStatus.COMMUNICATED,
    ) and instance.result and instance.result != LabAnalysisResult.EMPTY:
        FollowUpAction.objects.create(
            followup_case=case,
            action_type=FollowUpActionType.LAB_RESULT_ADDED,
            title=f"Résultat ajouté : {instance.test_type}",
            description=(
                f"Résultat : {instance.result}. "
                f"Statut : {instance.status}. "
                f"Laboratoire : {instance.lab_name}."
            ),
            performed_by=instance.validated_by,
            status=FollowUpActionStatus.COMPLETED,
            metadata={
                "sample_code": instance.sample.sample_code,
                "test_type": instance.test_type,
                "result": instance.result,
                "status": instance.status,
                "lab_analysis_uuid": str(instance.uuid),
            },
        )


@receiver(post_save, sender=LabAnalysis)
def _trigger_classification_on_positive_lab(sender, instance: LabAnalysis, created, **kwargs):
    """Phase 9D — auto-classification "confirmed" + alerte critique si POSITIF.

    Déclenché à la création du résultat positif OU à la validation
    (transition de status vers VALIDATED/COMMUNICATED avec result=positive).
    Idempotent : on n'écrase pas une classification déjà CONFIRMED.
    """
    if not instance.sample_id:
        return
    if instance.result != LabAnalysisResult.POSITIVE:
        return
    # On ne déclenche qu'à la validation/communication officielle
    if instance.status not in (
        LabAnalysisStatus.VALIDATED, LabAnalysisStatus.COMMUNICATED,
    ):
        return

    case = instance.sample.followup_case
    if case is None:
        return

    # Idempotence — déjà classifié CONFIRMED ?
    current = (
        CaseClassification.objects.filter(followup_case=case, is_current=True)
        .order_by("-classified_at")
        .first()
    )
    if current and current.classification == CaseClassificationCode.CONFIRMED:
        return

    try:
        from .tasks import _ensure_classification, _log_action  # type: ignore

        new_cls = _ensure_classification(
            case,
            code=CaseClassificationCode.CONFIRMED,
            reason=f"Résultat positif {instance.test_type} ({instance.lab_name})",
            classified_by=instance.validated_by,
        )
        _log_action(
            case,
            action_type=FollowUpActionType.ALERT_CREATED,
            title=f"Cas confirmé — {instance.test_type} positif",
            description=(
                f"Voyageur {case.traveler.public_id} — classification "
                f"automatiquement passée à CONFIRMED suite au résultat positif."
            ),
            metadata={
                "kind": "lab_positive_confirmation",
                "test_type": instance.test_type,
                "lab_name": instance.lab_name,
                "lab_analysis_uuid": str(instance.uuid),
                "classification_uuid": str(new_cls.uuid) if new_cls else None,
            },
        )
    except Exception:  # pragma: no cover - défense
        logger.exception("Auto-classification CONFIRMED KO (lab=%s)", instance.pk)

    # Alerte critique
    try:
        from apps.surveillance.services import trigger_alert

        trigger_alert(
            code=f"lab-positive-{instance.uuid}",
            title=f"Résultat positif — {case.traveler.public_id}",
            description=(
                f"Voyageur {case.traveler.public_id} — résultat positif "
                f"validé pour {instance.test_type} au {instance.lab_name}."
            ),
            severity="critical",
            disease=case.disease,
            target=case,
            metadata={
                "test_type": instance.test_type,
                "lab_name": instance.lab_name,
                "lab_analysis_uuid": str(instance.uuid),
            },
        )
    except Exception:  # pragma: no cover - best-effort
        logger.exception("Alerte lab positive KO (lab=%s)", instance.pk)


# ---------------------------------------------------------------------------
# CaseClassification — création
# ---------------------------------------------------------------------------


@receiver(post_save, sender=CaseClassification)
def _log_case_classified(sender, instance: CaseClassification, created, **kwargs):
    if not created:
        return
    FollowUpAction.objects.create(
        followup_case=instance.followup_case,
        action_type=FollowUpActionType.CASE_CLASSIFIED,
        title=f"Classification : {instance.classification}",
        description=instance.reason or "",
        performed_by=instance.classified_by,
        status=FollowUpActionStatus.COMPLETED,
        metadata={
            "classification": instance.classification,
            "classification_uuid": str(instance.uuid),
        },
    )

    case = instance.followup_case
    if instance.is_current and hasattr(case, "current_classification"):
        try:
            case.current_classification = instance.classification
            case.save(update_fields=["current_classification", "updated_at"])
        except Exception:  # pragma: no cover - défense
            pass
