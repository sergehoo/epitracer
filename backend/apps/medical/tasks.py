"""Tâches Celery du module `medical` (Phase 9A + 9D).

Phase 9A :
  - `medical.check_geolocation_compliance_all` : toutes les 6 h, vérifie
    que les voyageurs en suivi actif partagent leur géoloc consentie.

Phase 9D — automatisation du suivi sanitaire complet :
  - `medical.create_followup_schedule(traveler_id)` :
        crée la quarantaine + pré-crée les 21 DailyCheck à l'inscription.
  - `medical.send_daily_followup_reminders()` :
        rappel quotidien (cron 08:00) — version enrichie qui s'appuie sur
        `DiseaseFollowupProtocol.notification_schedule` au lieu de
        constantes hard-codées. Délègue à `companion.send_daily_checkin_reminders`
        pour les canaux (FCM/VAPID/SMS) puis enrichit la timeline médicale.
  - `medical.mark_missed_checkins()` :
        cron 23:00 — marque les DailyCheck du jour en `missed` quand aucun
        check-in voyageur n'a été reçu et qu'une notification avait été
        envoyée. Déclenche l'escalade si 2+ missed consécutifs (selon
        `protocol.escalation_rules.missed_checkins`).
  - `medical.escalate_critical_symptoms()` :
        balayage périodique (toutes les 30 min) en filet de sécurité
        derrière le signal `post_save MedicalSymptomReport`. Crée une
        HealthAlert + classification automatique `suspect`, notifie
        l'agent assigné et le district sanitaire.
  - `medical.escalate_critical_symptoms_for_case(case_id, ...)` :
        version ciblée appelée par signal (1 cas à la fois).
  - `medical.auto_close_completed_followups()` :
        cron 00:10 — clôt automatiquement les suivis arrivés à terme
        sans incident, selon `protocol.closure_rules`.
  - `medical.generate_followup_completion_certificate(case_id)` :
        PDF d'attestation MSHPCMU/INHP (ReportLab) stocké dans
        MEDIA_ROOT/followup_certificates/.

Contraintes :
  - toutes les tâches sont idempotentes (re-jouables sans dommage) ;
  - `bind=True`, `autoretry_for=(Exception,)`, `retry_backoff=30`,
    `max_retries=3` pour la résilience ;
  - aucune PII (téléphone, passeport) en clair dans les logs ou metadata ;
  - on utilise `traveler.public_id` partout comme identifiant
    non-PII (slug 24 chars destiné aux deep-links/logs).
"""
from __future__ import annotations

import io
import logging
import re
from datetime import date, timedelta
from typing import Optional

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.quarantine.models import (
    DailyCheck,
    DailyCheckStatus,
    QuarantineRecord,
    QuarantineStatus,
)

from .models import (
    CaseClassification,
    CaseClassificationCode,
    DiseaseFollowupProtocol,
    FollowUpAction,
    FollowUpActionStatus,
    FollowUpActionType,
    LabAnalysis,
    LabAnalysisResult,
    MedicalSymptomReport,
)
from .services import check_geolocation_compliance

logger = logging.getLogger("epidemitracker.medical.tasks")


# ----------------------------------------------------------------------------
# Helpers communs
# ----------------------------------------------------------------------------


def _mask_phone(phone: str | None) -> str:
    """Masque un numéro de téléphone pour les logs (RGPD friendly)."""
    if not phone:
        return ""
    s = re.sub(r"\s+", "", phone)
    if len(s) < 6:
        return "***"
    return f"{s[:5]}{s[5:7]}****{s[-3:]}"


def _public_id(traveler) -> str:
    return getattr(traveler, "public_id", "") or "?"


def _get_protocol(disease) -> Optional[DiseaseFollowupProtocol]:
    if disease is None:
        return None
    return (
        DiseaseFollowupProtocol.objects.filter(disease=disease, is_active=True)
        .first()
    )


def _today() -> date:
    return timezone.localdate()


def _system_user():
    """Retourne un user "système" pour signer les actions automatiques."""
    try:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.filter(is_superuser=True).order_by("pk").first()
    except Exception:  # pragma: no cover - resilience
        return None


def _ensure_classification(
    case: QuarantineRecord,
    *,
    code: str,
    reason: str,
    classified_by=None,
) -> CaseClassification | None:
    """Crée une nouvelle classification courante si ce n'est déjà la même.

    Marque les anciennes lignes `is_current=False` pour respecter l'invariant
    "1 seule classification courante par cas". Idempotent.
    """
    current = (
        CaseClassification.objects.filter(followup_case=case, is_current=True)
        .order_by("-classified_at")
        .first()
    )
    if current and current.classification == code:
        return current

    if classified_by is None:
        classified_by = case.assigned_agent or _system_user()

    if classified_by is None:
        logger.warning(
            "Pas d'utilisateur disponible pour la classification du cas %s — skip",
            case.pk,
        )
        return None

    with transaction.atomic():
        CaseClassification.objects.filter(
            followup_case=case, is_current=True,
        ).update(is_current=False)
        new = CaseClassification.objects.create(
            followup_case=case,
            classification=code,
            reason=reason,
            classified_by=classified_by,
            is_current=True,
        )
    return new


def _log_action(
    case: QuarantineRecord,
    *,
    action_type: str,
    title: str,
    description: str = "",
    metadata: dict | None = None,
    day: DailyCheck | None = None,
    user=None,
    status: str = FollowUpActionStatus.COMPLETED,
) -> FollowUpAction:
    """Helper qui crée un FollowUpAction sans PII en clair dans metadata."""
    safe_meta = {k: v for k, v in (metadata or {}).items() if v is not None}
    safe_meta.setdefault("traveler_public_id", _public_id(case.traveler))
    return FollowUpAction.objects.create(
        followup_case=case,
        followup_day=day,
        action_type=action_type,
        title=title[:200],
        description=description,
        performed_by=user,
        status=status,
        metadata=safe_meta,
    )


# ============================================================================
# 0) Tâche héritée Phase 9A — géolocalisation
# ============================================================================


@shared_task(name="medical.check_geolocation_compliance_all")
def check_geolocation_compliance_all() -> dict:
    """Vérifie la compliance géoloc de toutes les quarantaines actives."""
    qs = QuarantineRecord.objects.filter(status=QuarantineStatus.ACTIVE)
    scanned = 0
    compliant = 0
    alerts_raised = 0
    for case in qs.iterator(chunk_size=500):
        scanned += 1
        try:
            ok = check_geolocation_compliance(case)
        except Exception:  # pragma: no cover - défense
            logger.exception(
                "Erreur check_geolocation_compliance pour case=%s", case.pk,
            )
            continue
        if ok:
            compliant += 1
        else:
            alerts_raised += 1
    return {
        "scanned": scanned,
        "compliant": compliant,
        "alerts_raised": alerts_raised,
    }


# ============================================================================
# 1) create_followup_schedule(traveler_id)
# ============================================================================


@shared_task(
    bind=True,
    name="medical.create_followup_schedule",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def create_followup_schedule(self, traveler_id: int, disease_code: str | None = None) -> dict:
    """Initialise tout le suivi sanitaire d'un voyageur fraîchement enregistré.

    Algorithme :
      1. Récupère le voyageur + la maladie (Ebola par défaut).
      2. Récupère/crée le `DiseaseFollowupProtocol` actif pour cette maladie.
      3. Crée ou récupère le `QuarantineRecord` (start = today,
         end = today + duration_days du protocole).
      4. Pré-crée les `duration_days` `DailyCheck` (J1..JN, status="planned").
      5. Logge une action "Programmation du suivi créée".

    Idempotent : si la quarantaine existe déjà ET que les DailyCheck sont
    déjà créés, ne duplique rien. Retourne un dict avec compteurs.
    """
    from apps.travelers.models import Traveler
    from apps.diseases.models import Disease

    stats = {
        "traveler_id": traveler_id,
        "quarantine_created": False,
        "days_created": 0,
        "days_already_present": 0,
    }

    try:
        traveler = Traveler.objects.get(pk=traveler_id)
    except Traveler.DoesNotExist:
        logger.warning("create_followup_schedule: traveler #%s introuvable", traveler_id)
        return {**stats, "error": "traveler_not_found"}

    disease = None
    if disease_code:
        disease = Disease.objects.filter(code__iexact=disease_code).first()
    if disease is None:
        disease = (
            Disease.objects.filter(code__iexact="EBOLA").first()
            or Disease.objects.filter(code__iexact="ebola").first()
            or Disease.objects.first()
        )
    if disease is None:
        logger.error("create_followup_schedule: aucune maladie configurée — skip")
        return {**stats, "error": "no_disease_configured"}

    protocol = _get_protocol(disease)
    duration_days = int(getattr(protocol, "duration_days", None) or 21)

    today = _today()
    expected_end = today + timedelta(days=duration_days - 1)

    with transaction.atomic():
        case, created = QuarantineRecord.objects.get_or_create(
            traveler=traveler,
            disease=disease,
            status=QuarantineStatus.ACTIVE,
            defaults={
                "started_on": today,
                "expected_end_on": expected_end,
            },
        )
        stats["quarantine_created"] = created
        stats["quarantine_id"] = case.pk

        existing_days = set(
            DailyCheck.objects.filter(quarantine=case).values_list(
                "day_index", flat=True,
            )
        )
        to_create: list[DailyCheck] = []
        for day_no in range(1, duration_days + 1):
            if day_no in existing_days:
                stats["days_already_present"] += 1
                continue
            to_create.append(
                DailyCheck(
                    quarantine=case,
                    day_index=day_no,
                    check_date=case.started_on + timedelta(days=day_no - 1),
                    status=DailyCheckStatus.PLANNED,
                )
            )
        if to_create:
            DailyCheck.objects.bulk_create(to_create)
            stats["days_created"] = len(to_create)

        if created or stats["days_created"] > 0:
            _log_action(
                case,
                action_type=FollowUpActionType.MEDICAL_ORIENTATION,
                title=f"Programmation du suivi créée ({duration_days} jours)",
                description=(
                    f"Suivi {disease.code} initialisé pour le voyageur "
                    f"{_public_id(traveler)}. Période : "
                    f"{case.started_on:%Y-%m-%d} → {case.expected_end_on:%Y-%m-%d}. "
                    f"{stats['days_created']} jours planifiés."
                ),
                metadata={
                    "kind": "schedule_created",
                    "disease_code": disease.code,
                    "duration_days": duration_days,
                    "started_on": case.started_on.isoformat(),
                    "expected_end_on": case.expected_end_on.isoformat(),
                },
            )

    logger.info(
        "create_followup_schedule: traveler=%s case=%s created=%s days=%s",
        _public_id(traveler), case.pk, stats["quarantine_created"], stats["days_created"],
    )
    return stats


# ============================================================================
# 2) send_daily_followup_reminders()
# ============================================================================


@shared_task(
    bind=True,
    name="medical.send_daily_followup_reminders",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def send_daily_followup_reminders(self) -> dict:
    """Rappel quotidien — version enrichie protocole-aware.

    Délègue d'abord à `companion.send_daily_checkin_reminders` pour les
    canaux (FCM/VAPID/SMS/WhatsApp) puis enrichit la timeline médicale :
      - `FollowUpAction(NOTIFICATION_SENT)` côté médical ;
      - `DailyCheck.notification_sent = True` du jour courant.

    Respecte `protocol.notification_schedule.daily_reminder_hour` si défini.
    """
    try:
        from apps.companion.tasks import send_daily_checkin_reminders

        companion_stats = send_daily_checkin_reminders.run()
    except Exception:  # pragma: no cover - défense
        logger.exception("companion.send_daily_checkin_reminders a échoué")
        companion_stats = {}

    today = _today()
    stats = {
        "companion": companion_stats,
        "actions_logged": 0,
        "days_marked": 0,
    }

    qs = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler", "disease")

    for case in qs.iterator(chunk_size=500):
        if case.traveler is None:
            continue
        protocol = _get_protocol(case.disease)
        if protocol and protocol.notification_schedule:
            hour = protocol.notification_schedule.get("daily_reminder_hour")
            if isinstance(hour, int) and timezone.localtime().hour < hour:
                continue

        day = DailyCheck.objects.filter(
            quarantine=case, check_date=today,
        ).first()
        if day is None:
            continue
        if not day.notification_sent:
            day.notification_sent = True
            day.save(update_fields=["notification_sent", "updated_at"])
            stats["days_marked"] += 1

        already_logged = FollowUpAction.objects.filter(
            followup_case=case,
            action_type=FollowUpActionType.NOTIFICATION_SENT,
            followup_day=day,
        ).exists()
        if not already_logged:
            _log_action(
                case,
                action_type=FollowUpActionType.NOTIFICATION_SENT,
                title=f"Rappel quotidien — Jour {day.day_index}",
                description=(
                    f"Rappel envoyé au voyageur {_public_id(case.traveler)} "
                    f"(canaux gérés par companion). Téléphone masqué: "
                    f"{_mask_phone(case.traveler.phone_mobile)}."
                ),
                day=day,
                metadata={
                    "day_index": day.day_index,
                    "channels": {
                        k: v for k, v in companion_stats.items()
                        if k.endswith("_sent")
                    },
                },
            )
            stats["actions_logged"] += 1

    logger.info("medical.send_daily_followup_reminders summary: %s", stats)
    return stats


# ============================================================================
# 3) mark_missed_checkins()
# ============================================================================


@shared_task(
    bind=True,
    name="medical.mark_missed_checkins",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def mark_missed_checkins(self) -> dict:
    """Marque comme `missed` les check-ins planifiés non renseignés ce soir.

    Critères :
      - jour planifié pour aujourd'hui ;
      - notification_sent=True (le voyageur a bien été sollicité) ;
      - check_date == aujourd'hui ;
      - aucune réponse voyageur (has_symptoms=False ET temperature is NULL
        ET status est resté PLANNED/PENDING).

    Si X missed consécutifs (`protocol.escalation_rules.missed_checkins`,
    défaut 2), déclenche l'escalade.
    """
    today = _today()
    stats = {"scanned": 0, "marked_missed": 0, "escalated_for_missed": 0}

    qs = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler", "disease")

    for case in qs.iterator(chunk_size=500):
        stats["scanned"] += 1
        day = DailyCheck.objects.filter(
            quarantine=case, check_date=today,
        ).first()
        if day is None:
            continue
        if not day.notification_sent:
            continue
        if day.status not in (
            DailyCheckStatus.PLANNED, DailyCheckStatus.PENDING,
        ):
            continue
        responded = (
            day.has_symptoms
            or day.temperature_celsius is not None
            or bool(day.reported_by_user_id)
        )
        if responded:
            continue

        day.status = DailyCheckStatus.MISSED
        day.alert_raised = True
        day.save(update_fields=["status", "alert_raised", "updated_at"])
        stats["marked_missed"] += 1

        _log_action(
            case,
            action_type=FollowUpActionType.DAY_CLOSED,
            title=f"Check-in manqué jour {day.day_index}",
            description=(
                f"Aucune réponse voyageur reçue malgré rappel envoyé "
                f"({_public_id(case.traveler)})."
            ),
            day=day,
            metadata={
                "kind": "missed_checkin",
                "day_index": day.day_index,
                "check_date": today.isoformat(),
            },
        )

        protocol = _get_protocol(case.disease)
        missed_threshold = 2
        if protocol and protocol.escalation_rules:
            missed_threshold = int(
                protocol.escalation_rules.get("missed_checkins", 2) or 2
            )
        recent_missed = list(
            DailyCheck.objects.filter(
                quarantine=case,
                status=DailyCheckStatus.MISSED,
                check_date__lte=today,
            ).order_by("-check_date")[:missed_threshold]
        )
        if len(recent_missed) >= missed_threshold:
            day_indexes = sorted(d.day_index for d in recent_missed)
            if day_indexes[-1] - day_indexes[0] == missed_threshold - 1:
                try:
                    escalate_critical_symptoms_for_case.delay(
                        case.pk, reason="missed_checkins",
                    )
                    stats["escalated_for_missed"] += 1
                except Exception:  # pragma: no cover - dev sync fallback
                    escalate_critical_symptoms_for_case.run(
                        case.pk, reason="missed_checkins",
                    )
                    stats["escalated_for_missed"] += 1

    logger.info("mark_missed_checkins summary: %s", stats)
    return stats


# ============================================================================
# 4) escalate_critical_symptoms[_for_case]
# ============================================================================


def _notify_agent_and_district(case: QuarantineRecord, *, title: str, body: str) -> dict:
    """Envoie email + (best-effort) SMS à l'agent assigné. Erreurs swallowed."""
    sent = {"email": 0, "sms": 0}
    agent = case.assigned_agent
    if agent and getattr(agent, "email", None):
        try:
            from apps.notifications.providers import send_email

            res = send_email(agent.email, title, body)
            if getattr(res, "ok", False) or res:
                sent["email"] += 1
        except Exception:  # pragma: no cover - best-effort
            logger.exception("Notification email agent KO (case=%s)", case.pk)

    phone = getattr(agent, "phone_number", None) if agent else None
    if phone:
        try:
            from apps.notifications.services.dispatcher import enqueue_notification
            from apps.notifications.models import MessageType

            enqueue_notification(
                channel="sms",
                recipient=phone,
                body=body[:480],
                message_type=MessageType.AUTOMATIC_REMINDER,
                metadata={"kind": "medical_escalation", "case_id": case.pk},
            )
            sent["sms"] += 1
        except Exception:  # pragma: no cover - best-effort
            logger.exception("Notification SMS agent KO (case=%s)", case.pk)

    return sent


@shared_task(
    bind=True,
    name="medical.escalate_critical_symptoms_for_case",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def escalate_critical_symptoms_for_case(
    self, case_id: int, reason: str = "critical_symptom",
    symptom_code: str = "", symptom_report_id: int | None = None,
) -> dict:
    """Escalade un cas suite à symptôme critique (ou missed_checkins).

    1. HealthAlert(severity="critical") idempotente (code unique par
       case.uuid + reason).
    2. FollowUpAction(ESCALATED).
    3. Notifie agent assigné + district (email/SMS).
    4. closure_reason='escalated' + classification SUSPECT automatique.
    """
    from apps.surveillance.models import HealthAlert
    from apps.surveillance.services import trigger_alert

    stats = {"case_id": case_id, "alert_created": False, "classification_updated": False}

    try:
        case = QuarantineRecord.objects.select_related("traveler", "disease").get(pk=case_id)
    except QuarantineRecord.DoesNotExist:
        logger.warning("escalate_critical_symptoms_for_case: case=%s introuvable", case_id)
        return {**stats, "error": "case_not_found"}

    alert_code = f"esc-{case.uuid}-{reason}"
    if HealthAlert.objects.filter(code=alert_code).exists():
        logger.info("Alerte d'escalade %s déjà existante — idempotent skip", alert_code)
    else:
        if reason == "critical_symptom" and not symptom_code:
            last_critical = (
                MedicalSymptomReport.objects
                .filter(followup_case=case, is_critical=True)
                .order_by("-created_at")
                .first()
            )
            if last_critical:
                symptom_code = last_critical.symptom_code

        descr = (
            f"Voyageur {_public_id(case.traveler)} — escalade automatique "
            f"({reason}). Symptôme déclencheur : {symptom_code or 'n/a'}."
        )
        trigger_alert(
            code=alert_code,
            title=f"Cas escaladé : {symptom_code or reason}",
            description=descr,
            severity="critical",
            disease=case.disease,
            target=case,
            metadata={
                "reason": reason,
                "symptom_code": symptom_code,
                "case_id": case.pk,
                "case_uuid": str(case.uuid),
                "traveler_public_id": _public_id(case.traveler),
            },
        )
        stats["alert_created"] = True

    _log_action(
        case,
        action_type=FollowUpActionType.ESCALATED,
        title=(
            f"Cas escaladé : symptôme {symptom_code}"
            if symptom_code else f"Cas escaladé : {reason}"
        ),
        description=f"Escalade automatique déclenchée — motif: {reason}.",
        metadata={
            "reason": reason,
            "symptom_code": symptom_code,
            "symptom_report_id": symptom_report_id,
            "alert_code": alert_code,
        },
    )

    if case.closure_reason != "escalated":
        case.closure_reason = "escalated"
        try:
            case.save(update_fields=["closure_reason", "updated_at"])
        except Exception:  # pragma: no cover
            logger.exception("Maj closure_reason KO (case=%s)", case.pk)

    new_cls = _ensure_classification(
        case,
        code=CaseClassificationCode.SUSPECT,
        reason=f"Escalade automatique — {reason} / {symptom_code or 'n/a'}",
    )
    if new_cls is not None:
        stats["classification_updated"] = True

    title = f"[EpiTrace] Escalade — {_public_id(case.traveler)}"
    body = (
        f"Voyageur {_public_id(case.traveler)} en suivi "
        f"{case.disease.code if case.disease_id else '?'} "
        f"escaladé suite à : {reason}. Symptôme : {symptom_code or 'n/a'}. "
        f"Connectez-vous à EpiTrace pour traiter."
    )
    notif_stats = _notify_agent_and_district(case, title=title, body=body)
    stats["notified"] = notif_stats

    logger.info("escalate_critical_symptoms_for_case: %s", stats)
    return stats


@shared_task(
    bind=True,
    name="medical.escalate_critical_symptoms",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def escalate_critical_symptoms(self) -> dict:
    """Filet de sécurité — backup périodique du signal (60 dernières minutes)."""
    cutoff = timezone.now() - timedelta(hours=1)
    qs = MedicalSymptomReport.objects.filter(
        is_critical=True, created_at__gte=cutoff,
    ).select_related("followup_case", "followup_case__traveler", "followup_case__disease")

    stats = {"scanned": 0, "escalated": 0}
    for report in qs.iterator(chunk_size=200):
        stats["scanned"] += 1
        case = report.followup_case
        if case is None:
            continue
        already = FollowUpAction.objects.filter(
            followup_case=case,
            action_type=FollowUpActionType.ESCALATED,
            metadata__symptom_report_id=report.pk,
        ).exists()
        if already:
            continue
        try:
            escalate_critical_symptoms_for_case.delay(
                case.pk,
                reason="critical_symptom",
                symptom_code=report.symptom_code,
                symptom_report_id=report.pk,
            )
            stats["escalated"] += 1
        except Exception:  # pragma: no cover - dev sync fallback
            escalate_critical_symptoms_for_case.run(
                case.pk,
                reason="critical_symptom",
                symptom_code=report.symptom_code,
                symptom_report_id=report.pk,
            )
            stats["escalated"] += 1

    logger.info("escalate_critical_symptoms backup scan: %s", stats)
    return stats


# ============================================================================
# 5) auto_close_completed_followups()
# ============================================================================


def _can_close(case: QuarantineRecord, protocol: DiseaseFollowupProtocol | None) -> tuple[bool, str]:
    """Évalue les conditions de clôture selon protocol.closure_rules."""
    rules = (protocol.closure_rules if protocol else None) or {}
    duration = int((protocol.duration_days if protocol else 21) or 21)

    today = _today()
    days_elapsed = (today - case.started_on).days + 1 if case.started_on else 0
    required_days = int(rules.get("days_completed", duration) or duration)
    if days_elapsed < required_days:
        return False, "duration_not_reached"

    if rules.get("no_critical_symptom", True):
        critical_exists = MedicalSymptomReport.objects.filter(
            followup_case=case, is_critical=True,
        ).exists()
        if critical_exists:
            return False, "critical_symptom_present"

    if rules.get("no_positive_lab", True):
        positive_exists = LabAnalysis.objects.filter(
            sample__followup_case=case, result=LabAnalysisResult.POSITIVE,
        ).exists()
        if positive_exists:
            return False, "positive_lab_result"

    max_missed = int(rules.get("max_missed_checkins", 9999))
    missed = DailyCheck.objects.filter(
        quarantine=case, status=DailyCheckStatus.MISSED,
    ).count()
    if missed > max_missed:
        return False, f"too_many_missed_{missed}"

    return True, "ok"


@shared_task(
    bind=True,
    name="medical.auto_close_completed_followups",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def auto_close_completed_followups(self) -> dict:
    """Clôt automatiquement les suivis arrivés à terme sans incident."""
    stats = {
        "scanned": 0, "closed": 0, "blocked": 0, "certificates_queued": 0,
    }
    today = _today()

    qs = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler", "disease")

    for case in qs.iterator(chunk_size=500):
        if case.expected_end_on and case.expected_end_on > today:
            continue
        stats["scanned"] += 1
        protocol = _get_protocol(case.disease)
        can, why = _can_close(case, protocol)

        if not can:
            stats["blocked"] += 1
            already_today = FollowUpAction.objects.filter(
                followup_case=case,
                action_type=FollowUpActionType.DAY_CLOSED,
                metadata__kind="closure_blocked",
                performed_at__date=today,
            ).exists()
            if not already_today:
                _log_action(
                    case,
                    action_type=FollowUpActionType.DAY_CLOSED,
                    title=f"Clôture automatique bloquée — {why}",
                    description=(
                        f"La période protocolaire est atteinte mais une "
                        f"condition de clôture n'est pas remplie ({why})."
                    ),
                    metadata={"kind": "closure_blocked", "reason": why},
                    status=FollowUpActionStatus.PLANNED,
                )
            continue

        duration = (case.expected_end_on - case.started_on).days + 1 if case.started_on else 21
        with transaction.atomic():
            case.status = QuarantineStatus.COMPLETED
            case.actual_end_on = today
            case.closure_reason = "auto_completed_after_protocol_duration"
            case.save(update_fields=[
                "status", "actual_end_on", "closure_reason", "updated_at",
            ])
            _log_action(
                case,
                action_type=FollowUpActionType.FOLLOWUP_CLOSED,
                title=f"Suivi clôturé automatiquement après {duration} jours sans incident",
                description=(
                    f"Aucune condition d'alerte n'a été détectée — clôture "
                    f"automatique du suivi du voyageur {_public_id(case.traveler)}."
                ),
                metadata={
                    "kind": "auto_closed",
                    "duration_days": duration,
                    "started_on": case.started_on.isoformat() if case.started_on else None,
                    "actual_end_on": today.isoformat(),
                },
            )
            _ensure_classification(
                case,
                code=CaseClassificationCode.CLOSED,
                reason="auto_closed_after_protocol_duration",
            )
        stats["closed"] += 1

        try:
            from apps.companion.push import push_notify

            push_notify(
                traveler=case.traveler,
                title="Période d'accompagnement terminée",
                body=(
                    "Merci ! Votre période de surveillance sanitaire est "
                    "terminée. Une attestation est disponible."
                ),
                url=f"/voyageur/suivi?id={_public_id(case.traveler)}",
                tag="followup-complete",
                notification_type="followup_complete",
            )
        except Exception:  # pragma: no cover - best-effort
            logger.exception("Notif fin de suivi KO (case=%s)", case.pk)

        try:
            generate_followup_completion_certificate.delay(case.pk)
            stats["certificates_queued"] += 1
        except Exception:  # pragma: no cover - dev sync fallback
            try:
                generate_followup_completion_certificate.run(case.pk)
                stats["certificates_queued"] += 1
            except Exception:
                logger.exception("Génération PDF attestation KO (case=%s)", case.pk)

    logger.info("auto_close_completed_followups summary: %s", stats)
    return stats


# ============================================================================
# 6) generate_followup_completion_certificate(case_id)
# ============================================================================


def _certificate_relative_path(case: QuarantineRecord) -> str:
    return f"followup_certificates/{case.uuid}.pdf"


def _render_completion_certificate_pdf(case: QuarantineRecord) -> bytes:
    """Génère un PDF basique d'attestation MSHPCMU/INHP (A4, 1 page).

    Mise à niveau visuelle prévue en Phase 9E.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # En-tête sombre
    c.setFillColorRGB(0.05, 0.20, 0.40)
    c.rect(0, height - 24 * mm, width, 24 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, height - 11 * mm, "REPUBLIQUE DE COTE D'IVOIRE")
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, height - 15 * mm, "Union - Discipline - Travail")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(
        width / 2, height - 20 * mm,
        "Ministere de la Sante, de l'Hygiene Publique et de la CMU - INHP",
    )

    # Barre tricolore (orange / blanc / vert)
    band_y = height - 28 * mm
    third = width / 3
    c.setFillColorRGB(1.0, 0.502, 0.0)
    c.rect(0, band_y, third, 4 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.rect(third, band_y, third, 4 * mm, fill=1, stroke=0)
    c.setFillColorRGB(0.0, 0.502, 0.376)
    c.rect(2 * third, band_y, third, 4 * mm, fill=1, stroke=0)

    # Titre
    c.setFillColorRGB(0.05, 0.20, 0.40)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 50 * mm,
                        "ATTESTATION DE FIN DE SUIVI SANITAIRE")
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(width / 2, height - 56 * mm,
                        "Programme national de surveillance epidemiologique des voyageurs")

    # Texte
    traveler = case.traveler
    full_name = f"{(traveler.last_name or '').upper()} {traveler.first_name or ''}".strip() or "-"
    started = case.started_on.strftime("%d/%m/%Y") if case.started_on else "-"
    ended_dt = (case.actual_end_on or case.expected_end_on)
    ended = ended_dt.strftime("%d/%m/%Y") if ended_dt else "-"
    duration = (
        ((case.actual_end_on or case.expected_end_on) - case.started_on).days + 1
        if case.started_on else 21
    )
    disease_name = case.disease.name if case.disease_id else "-"

    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica", 11)
    c.drawString(25 * mm, height - 80 * mm,
                 "L'Institut National d'Hygiene Publique (INHP) atteste que :")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(25 * mm, height - 100 * mm, full_name)
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(25 * mm, height - 106 * mm,
                 f"Identifiant voyageur : {_public_id(traveler)}")

    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont("Helvetica", 11)
    txt = c.beginText(25 * mm, height - 120 * mm)
    txt.setLeading(16)
    for line in [
        f"a ete place sous surveillance sanitaire pour la maladie suivante :",
        f"  - {disease_name}",
        "",
        f"du {started} au {ended}, soit {duration} jours.",
        "",
        "A l'issue de cette periode de surveillance, aucun symptome",
        "critique ni resultat de laboratoire defavorable n'a ete constate.",
        "Le suivi est cloture automatiquement apres respect integral du",
        "protocole sanitaire defini par le Ministere de la Sante.",
    ]:
        txt.textLine(line)
    c.drawText(txt)

    # Encadré OK
    c.setFillColorRGB(0.0, 0.502, 0.376)
    c.roundRect(25 * mm, 80 * mm, 160 * mm, 14 * mm, 4, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, 88 * mm,
                        "SUIVI CLOTURE - AUCUN INCIDENT CONSTATE")

    # Signature
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.setFont("Helvetica-Oblique", 9)
    issued_at = timezone.now()
    c.drawString(25 * mm, 60 * mm,
                 f"Delivre le : {issued_at.strftime('%d/%m/%Y a %H:%M')}")
    c.drawString(25 * mm, 55 * mm,
                 f"Reference : {case.uuid} . Signature electronique INHP")
    c.drawString(25 * mm, 50 * mm,
                 "Document genere automatiquement.")

    # Footer
    c.setFillColorRGB(0.05, 0.20, 0.40)
    c.rect(0, 0, width, 12 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 5 * mm,
                        "INHP - Plateforme EpiTrace - Surveillance epidemiologique nationale")

    c.showPage()
    c.save()
    return buf.getvalue()


@shared_task(
    bind=True,
    name="medical.generate_followup_completion_certificate",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def generate_followup_completion_certificate(self, case_id: int) -> dict:
    """Génère un PDF d'attestation et le stocke dans MEDIA_ROOT.

    Idempotent : si le fichier existe déjà, on renvoie son chemin sans
    régénérer. Pour forcer la régénération, supprimer le fichier au
    préalable.
    """
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    stats = {"case_id": case_id, "generated": False}
    try:
        case = QuarantineRecord.objects.select_related(
            "traveler", "disease",
        ).get(pk=case_id)
    except QuarantineRecord.DoesNotExist:
        return {**stats, "error": "case_not_found"}

    rel_path = _certificate_relative_path(case)
    if default_storage.exists(rel_path):
        logger.info("Certificat déjà présent : %s — idempotent skip", rel_path)
        return {**stats, "path": rel_path, "skipped": "exists"}

    pdf_bytes = _render_completion_certificate_pdf(case)
    saved_path = default_storage.save(rel_path, ContentFile(pdf_bytes))
    stats["generated"] = True
    stats["path"] = saved_path

    already = FollowUpAction.objects.filter(
        followup_case=case,
        action_type=FollowUpActionType.FOLLOWUP_CLOSED,
        metadata__kind="certificate_generated",
    ).exists()
    if not already:
        _log_action(
            case,
            action_type=FollowUpActionType.FOLLOWUP_CLOSED,
            title="Attestation de fin de suivi générée",
            description=(
                f"PDF d'attestation INHP/MSHPCMU disponible pour le voyageur "
                f"{_public_id(case.traveler)}."
            ),
            metadata={
                "kind": "certificate_generated",
                "path": saved_path,
                "phase": "9D_basic_pdf",
                "todo": "PHASE_9E_design_enrichment",
            },
        )

    logger.info("generate_followup_completion_certificate: case=%s path=%s",
                case.pk, saved_path)
    return stats


# ============================================================================
# 7) Documents Phase 9E — fiche individuelle / prélèvement / orientation
# ============================================================================


def _individual_sheet_relative_path(case: QuarantineRecord) -> str:
    return f"medical/sheets/{case.uuid}.pdf"


def _sample_report_relative_path(sample) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", sample.sample_code or f"sample-{sample.pk}")
    return f"medical/samples/{safe}.pdf"


def _orientation_relative_path(case: QuarantineRecord, agent_id: int | None) -> str:
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-by{agent_id}" if agent_id else ""
    return f"medical/orientations/{case.uuid}-{ts}{suffix}.pdf"


@shared_task(
    bind=True,
    name="medical.generate_followup_individual_sheet",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def generate_followup_individual_sheet(self, case_id: int) -> dict:
    """Génère la fiche de suivi individuelle PDF + stocke /media/medical/sheets/.

    Idempotent : re-génère si le fichier existe déjà (le contenu peut avoir
    évolué — c'est un dossier vivant). Pour économiser le stockage,
    une nouvelle exécution écrase le précédent fichier.
    """
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    from .services_pdf import render_followup_individual_sheet

    stats = {"case_id": case_id, "generated": False}
    try:
        case = QuarantineRecord.objects.select_related(
            "traveler", "disease",
        ).get(pk=case_id)
    except QuarantineRecord.DoesNotExist:
        return {**stats, "error": "case_not_found"}

    pdf_bytes = render_followup_individual_sheet(case)
    rel_path = _individual_sheet_relative_path(case)

    # Écrasement contrôlé : on supprime l'ancienne version si elle existe
    if default_storage.exists(rel_path):
        try:
            default_storage.delete(rel_path)
        except Exception:  # pragma: no cover - best-effort
            logger.exception("Suppression ancien PDF KO (%s)", rel_path)

    saved_path = default_storage.save(rel_path, ContentFile(pdf_bytes))
    stats["generated"] = True
    stats["path"] = saved_path

    _log_action(
        case,
        action_type=FollowUpActionType.MEDICAL_ORIENTATION,
        title="Fiche de suivi individuelle générée",
        description=(
            f"PDF de la fiche complète régénéré pour le voyageur "
            f"{_public_id(case.traveler)}."
        ),
        metadata={
            "kind": "document_generated",
            "document_type": "individual_sheet",
            "path": saved_path,
        },
    )

    logger.info(
        "generate_followup_individual_sheet: case=%s path=%s",
        case.pk, saved_path,
    )
    return stats


@shared_task(
    bind=True,
    name="medical.generate_sample_collection_report",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def generate_sample_collection_report_task(self, sample_id: int) -> dict:
    """Génère le rapport de prélèvement PDF + stocke /media/medical/samples/."""
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    from .models import MedicalSample
    from .services_pdf import render_sample_collection_report

    stats = {"sample_id": sample_id, "generated": False}
    try:
        sample = (
            MedicalSample.objects
            .select_related("followup_case", "followup_case__traveler",
                            "followup_case__disease", "collected_by")
            .get(pk=sample_id)
        )
    except MedicalSample.DoesNotExist:
        return {**stats, "error": "sample_not_found"}

    pdf_bytes = render_sample_collection_report(sample)
    rel_path = _sample_report_relative_path(sample)

    if default_storage.exists(rel_path):
        try:
            default_storage.delete(rel_path)
        except Exception:  # pragma: no cover - best-effort
            logger.exception("Suppression ancien PDF KO (%s)", rel_path)

    saved_path = default_storage.save(rel_path, ContentFile(pdf_bytes))
    stats["generated"] = True
    stats["path"] = saved_path

    case = sample.followup_case
    if case is not None:
        _log_action(
            case,
            action_type=FollowUpActionType.SAMPLE_REQUESTED,
            title=f"Rapport de prélèvement généré ({sample.sample_code})",
            description=(
                f"PDF d'accompagnement laboratoire généré pour le prélèvement "
                f"{sample.sample_code}."
            ),
            metadata={
                "kind": "document_generated",
                "document_type": "sample_report",
                "sample_id": sample.pk,
                "sample_code": sample.sample_code,
                "path": saved_path,
            },
        )

    logger.info(
        "generate_sample_collection_report: sample=%s path=%s",
        sample.pk, saved_path,
    )
    return stats


@shared_task(
    bind=True,
    name="medical.generate_medical_orientation_form",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
)
def generate_medical_orientation_form_task(
    self, case_id: int, agent_id: int | None = None,
) -> dict:
    """Génère la fiche d'orientation PDF + stocke /media/medical/orientations/."""
    from django.contrib.auth import get_user_model
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile

    from .services_pdf import render_medical_orientation_form

    stats = {"case_id": case_id, "agent_id": agent_id, "generated": False}
    try:
        case = QuarantineRecord.objects.select_related(
            "traveler", "disease",
        ).get(pk=case_id)
    except QuarantineRecord.DoesNotExist:
        return {**stats, "error": "case_not_found"}

    agent = None
    if agent_id:
        User = get_user_model()
        agent = User.objects.filter(pk=agent_id).first()

    pdf_bytes = render_medical_orientation_form(case, agent=agent)
    rel_path = _orientation_relative_path(case, agent_id)

    saved_path = default_storage.save(rel_path, ContentFile(pdf_bytes))
    stats["generated"] = True
    stats["path"] = saved_path

    _log_action(
        case,
        action_type=FollowUpActionType.MEDICAL_ORIENTATION,
        title="Fiche d'orientation médicale générée",
        description=(
            f"PDF d'orientation médicale généré pour le voyageur "
            f"{_public_id(case.traveler)}."
        ),
        user=agent,
        metadata={
            "kind": "document_generated",
            "document_type": "orientation",
            "agent_id": agent_id,
            "path": saved_path,
        },
    )

    logger.info(
        "generate_medical_orientation_form: case=%s agent=%s path=%s",
        case.pk, agent_id, saved_path,
    )
    return stats
