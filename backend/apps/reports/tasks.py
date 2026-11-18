"""Tâches Celery du sous-module rapports hebdomadaires automatisés.

Orchestration :
    dispatch_weekly_report()  (Beat, lundi 08h00 Africa/Abidjan)
        └─ generate_weekly_report()  (agrège + PDF + Excel + persist)
        └─ deliver_weekly_report(report_id)  (email puis SMS)
    Une génération manuelle réussie met aussi l'envoi en file.

Un seul journal par (rapport, destinataire, canal) : un destinataire déjà servi
ne reçoit jamais le rapport une seconde fois.

Tâches périodiques auxiliaires :
    - retry_failed_weekly_reports()      : relances bornées, états bloqués, rattrapage
    - cleanup_expired_report_files()     : purge fichiers > 90j

Toutes les tâches sont *idempotentes* : re-jouer 2x n'a aucun effet de bord
double (voir invariant #2 de l'intent-compile). Verrou basé sur la contrainte
UNIQUE (report_type, period_start, period_end) de GeneratedReport.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from .metrics import (
    REPORT_DELIVERY_FAILED_TOTAL, REPORT_EMAIL_SENT_TOTAL,
    REPORT_GENERATION_DURATION, REPORT_SMS_SENT_TOTAL,
    REPORTS_FAILED_TOTAL, REPORTS_GENERATED_TOTAL,
    refresh_recipients_gauge,
)

logger = logging.getLogger("epidemitracker.reports.tasks")


# ---------------------------------------------------------------------------
# 1. Génération du rapport hebdomadaire (agrège + PDF + Excel)
# ---------------------------------------------------------------------------
@shared_task(
    bind=True,
    name="reports.generate_weekly_report",
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
    queue="reports",
)
def generate_weekly_report(self, period_start_iso: Optional[str] = None,
                           period_end_iso: Optional[str] = None,
                           triggered_by_user_id: Optional[int] = None,
                           deliver: bool = True) -> int:
    """Génère le rapport de la semaine.

    Args:
        period_start_iso : ISO datetime (défaut = semaine précédente auto)
        period_end_iso   : ISO datetime (défaut = semaine précédente auto)
        triggered_by_user_id : pk User si déclenché manuellement
        deliver : après génération réussie, met l'envoi en file (idempotent :
            les destinataires déjà servis ne reçoivent rien de plus)

    Returns:
        pk du GeneratedReport créé/existant (idempotent).
    """
    from apps.reports.models import (
        GeneratedReport, ReportStatus, ReportType,
    )
    from apps.reports.services.weekly_aggregator import (
        aggregate_weekly, previous_week_period,
    )
    from apps.reports.services.weekly_excel import render_weekly_xlsx
    from apps.reports.services.weekly_pdf import render_weekly_pdf

    # Résolution période (soit fournie, soit semaine précédente auto)
    if period_start_iso and period_end_iso:
        period_start = datetime.fromisoformat(period_start_iso)
        period_end = datetime.fromisoformat(period_end_iso)
    else:
        period_start, period_end = previous_week_period()

    # Idempotence forte : cherche un rapport existant pour (type, start, end)
    existing = GeneratedReport.objects.filter(
        report_type=ReportType.WEEKLY,
        period_start=period_start,
        period_end=period_end,
    ).first()

    if existing and existing.status == ReportStatus.READY:
        logger.info(
            "[reports] rapport hebdo déjà généré et READY — skip (id=%s code=%s)",
            existing.pk, existing.report_code,
        )
        _maybe_deliver(deliver, existing.pk)
        return existing.pk

    # Verrou : SELECT_FOR_UPDATE sur la ligne pour éviter concurrence
    with transaction.atomic():
        if existing:
            report = GeneratedReport.objects.select_for_update().get(pk=existing.pk)
            report.status = ReportStatus.GENERATING
            report.error_message = ""
            report.save(update_fields=["status", "error_message", "updated_at"])
        else:
            try:
                report = GeneratedReport.objects.create(
                    report_type=ReportType.WEEKLY,
                    period_start=period_start,
                    period_end=period_end,
                    status=ReportStatus.GENERATING,
                    generated_by_id=triggered_by_user_id,
                )
            except IntegrityError:
                # Race condition : un autre worker a créé le même report en //
                report = GeneratedReport.objects.get(
                    report_type=ReportType.WEEKLY,
                    period_start=period_start, period_end=period_end,
                )
                if report.status == ReportStatus.READY:
                    _maybe_deliver(deliver, report.pk)
                    return report.pk

    # Agrégation (hors transaction, potentiellement long)
    try:
        agg = aggregate_weekly(period_start, period_end)

        # PDF (toujours)
        pdf_bytes = render_weekly_pdf(agg)
        report.pdf_file.save(
            f"{report.report_code}.pdf",
            ContentFile(pdf_bytes),
            save=False,
        )

        # Excel (best-effort — fallback CSV si openpyxl absent)
        try:
            xlsx_bytes = render_weekly_xlsx(agg)
            ext = "xlsx" if xlsx_bytes[:2] == b"PK" else "csv"
            report.excel_file.save(
                f"{report.report_code}.{ext}",
                ContentFile(xlsx_bytes),
                save=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[reports] Excel/CSV render failed for %s: %s",
                           report.report_code, exc)

        report.summary_data = agg
        report.status = ReportStatus.READY
        report.generated_at = timezone.now()
        report.duration_ms = agg.get("meta", {}).get("generation_ms", 0)
        report.save()

        logger.info("[reports] rapport %s généré (%s ms, %s KB PDF)",
                    report.report_code, report.duration_ms,
                    round(len(pdf_bytes) / 1024))

        # Métriques Prometheus
        REPORTS_GENERATED_TOTAL.labels(report_type=str(report.report_type)).inc()
        REPORT_GENERATION_DURATION.labels(
            report_type=str(report.report_type),
        ).observe(report.duration_ms / 1000.0)

    except Exception as exc:
        logger.exception("[reports] génération %s a échoué : %s",
                         report.report_code, exc)
        report.status = ReportStatus.FAILED
        report.error_message = str(exc)[:1000]
        report.save(update_fields=["status", "error_message", "updated_at"])
        REPORTS_FAILED_TOTAL.labels(
            report_type=str(report.report_type),
            reason=type(exc).__name__,
        ).inc()
        raise

    _maybe_deliver(deliver, report.pk)
    return report.pk


# ---------------------------------------------------------------------------
# 2. Envoi — un seul journal par (rapport, destinataire, canal)
# ---------------------------------------------------------------------------
# Relance automatique bornée : 5 min → 10 min → 20 min, puis échec définitif.
MAX_AUTO_RETRIES = 3
# Au-delà, un envoi « en file » sans issue côté notifications est réexaminé.
STALE_DELIVERY_AFTER = timedelta(minutes=30)
# Une génération ne dure que quelques secondes : au-delà, la tâche est perdue.
STALE_GENERATION_AFTER = timedelta(hours=1)
# Rapports récents dont l'envoi est (re)pris par la tâche périodique, au cas
# où sa mise en file après génération aurait échoué.
CATCH_UP_WINDOW = timedelta(hours=48)


class _PiiInSmsError(Exception):
    def __init__(self, violations):
        super().__init__("PII detected in SMS body")
        self.violations = violations


def _schedule_delivery(report_id: int) -> None:
    """Met l'envoi en file sans bloquer l'appelant (requête web ou génération).

    Si le broker est injoignable, la tâche périodique `retry_failed_weekly_reports`
    reprend l'envoi des rapports récents : rien n'est perdu.
    """
    try:
        deliver_weekly_report.delay(report_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[reports] envoi du rapport %s non mis en file (%s) : "
                       "reprise par la tâche périodique", report_id, exc)


def _maybe_deliver(deliver: bool, report_id: int) -> None:
    if deliver:
        _schedule_delivery(report_id)


def _eligible_recipients(report, channel: str) -> list:
    from apps.reports.models import AutomatedReportRecipient, PreferredChannel

    own = PreferredChannel.EMAIL if channel == "email" else PreferredChannel.SMS
    qs = AutomatedReportRecipient.objects.filter(
        is_active=True,
        consent_date__isnull=False,  # AC-08 : consentement obligatoire
        preferred_channel__in=(own, PreferredChannel.BOTH),
    )
    qs = qs.exclude(email="") if channel == "email" else qs.exclude(phone_number="")
    return [
        r for r in qs
        if not r.allowed_report_types or report.report_type in r.allowed_report_types
    ]


def _render_delivery(report, channel: str) -> tuple[str, str]:
    """(corps, objet) du message ; refuse un SMS contenant des PII (invariant #3)."""
    if channel == "email":
        from apps.reports.services.weekly_email import render_weekly_email_html

        body = render_weekly_email_html(
            report.summary_data, download_url="", pdf_attached=False,
        )
        return body, f"[EpiTrace] Rapport hebdomadaire — {report.report_code}"
    from apps.reports.services.weekly_sms import render_weekly_sms, validate_no_pii

    body = render_weekly_sms(report.summary_data)
    is_clean, violations = validate_no_pii(body)
    if not is_clean:
        raise _PiiInSmsError(violations)
    return body, ""


def _latest_logs(qs):
    """Dernier journal de chaque (rapport, destinataire, canal).

    Les anciens envois manuels ont pu créer plusieurs journaux pour un même
    destinataire : seul le plus récent fait foi (statistiques, relances).
    """
    from django.db.models import Exists, OuterRef

    from apps.reports.models import ReportDeliveryLog

    newer = ReportDeliveryLog.objects.filter(
        report=OuterRef("report"), recipient=OuterRef("recipient"),
        channel=OuterRef("channel"), created_at__gt=OuterRef("created_at"),
    )
    return qs.annotate(_superseded=Exists(newer)).filter(_superseded=False)


def _claim_new_delivery(report, rec, channel: str):
    """Crée le journal (rapport, destinataire, canal) s'il n'existe pas encore.

    Le verrou sur le rapport sérialise les envois concurrents (Beat rejoué,
    génération manuelle) : un destinataire déjà servi ne reçoit rien de plus.
    """
    from apps.reports.models import DeliveryStatus, GeneratedReport, ReportDeliveryLog

    with transaction.atomic():
        GeneratedReport.objects.select_for_update().get(pk=report.pk)
        if ReportDeliveryLog.objects.filter(
            report=report, recipient=rec, channel=channel,
        ).exists():
            return None
        return ReportDeliveryLog.objects.create(
            report=report, recipient=rec, channel=channel,
            destination_masked=(
                _mask_email(rec.email) if channel == "email" else rec.masked_phone
            ),
            status=DeliveryStatus.QUEUED,
        )


def _dispatch(log, *, body: str, subject: str = "") -> str:
    """Met la notification en file pour ce journal ; retourne sent/failed/queued."""
    from apps.notifications.services.dispatcher import enqueue_notification
    from apps.notifications.services.errors import classify_error

    rec, report = log.recipient, log.report
    try:
        result = enqueue_notification(
            channel=log.channel,
            recipient=rec.email if log.channel == "email" else rec.phone_number,
            body=body,
            subject=subject,
            traveler=None,  # rapport global, pas lié à un voyageur
            message_type="admin_notice",
            metadata={"kind": "weekly_report", "report_id": report.pk},
            # Une notification par tentative : un même envoi rejoué en
            # concurrence n'est jamais expédié deux fois.
            dedup_key=f"weekly-report:{report.pk}:{rec.pk}:{log.channel}:{log.retry_count}",
        )
        outcome = _apply_dispatch_result(log, result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[reports] envoi %s vers %s en erreur : %s",
                         log.channel, log.destination_masked, exc)
        _mark_failed(log, str(exc), classify_error(str(exc)))
        outcome = "failed"
    log.save()

    report_type = str(report.report_type)
    if outcome == "failed":
        REPORT_DELIVERY_FAILED_TOTAL.labels(
            report_type=report_type, channel=log.channel, reason="provider_error",
        ).inc()
    elif log.channel == "email":
        REPORT_EMAIL_SENT_TOTAL.labels(report_type=report_type).inc()
    else:
        REPORT_SMS_SENT_TOTAL.labels(
            report_type=report_type, provider=str(log.provider or "unknown"),
        ).inc()
    return outcome


def _deliver_channel(report, channel: str) -> dict:
    """Envoie le rapport sur un canal aux destinataires actifs pas encore servis."""
    counts = {"sent": 0, "failed": 0, "queued": 0, "skipped": 0}
    recipients = _eligible_recipients(report, channel)
    if not recipients:
        return counts
    body, subject = _render_delivery(report, channel)
    for rec in recipients:
        log = _claim_new_delivery(report, rec, channel)
        if log is None:
            counts["skipped"] += 1
            continue
        counts[_dispatch(log, body=body, subject=subject)] += 1
    logger.info("[reports] %s %s : %s", channel, report.report_code, counts)
    return counts


def _send_channel(report_id: int, channel: str) -> dict:
    from apps.reports.models import GeneratedReport, ReportStatus

    report = GeneratedReport.objects.get(pk=report_id)
    if report.status != ReportStatus.READY:
        return {"ok": False, "reason": f"Report status={report.status}"}
    try:
        counts = _deliver_channel(report, channel)
    except _PiiInSmsError as exc:
        logger.error("[reports] SMS refusé — PII détectée dans %s : %s",
                     report.report_code, exc.violations)
        return {"ok": False, "reason": str(exc), "violations": exc.violations}
    return {"ok": True, **counts, "report_code": report.report_code}


@shared_task(bind=True, name="reports.send_weekly_report_email", queue="notifications")
def send_weekly_report_email(self, report_id: int) -> dict:
    """Envoie le rapport par email aux destinataires actifs pas encore servis."""
    return _send_channel(report_id, "email")


@shared_task(bind=True, name="reports.send_weekly_report_sms", queue="notifications")
def send_weekly_report_sms(self, report_id: int) -> dict:
    """Envoie le SMS synthétique (bloqué si PII détectée — invariant #3)."""
    return _send_channel(report_id, "sms")


@shared_task(bind=True, name="reports.deliver_weekly_report", queue="notifications")
def deliver_weekly_report(self, report_id: int) -> dict:
    """Envoi automatique après génération : email puis SMS, chacun isolé."""
    results = {}
    for channel in ("email", "sms"):
        try:
            results[channel] = _send_channel(report_id, channel)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[reports] envoi %s du rapport %s : %s",
                             channel, report_id, exc)
            results[channel] = {"ok": False, "error": str(exc)}
    return {"report_id": report_id, **results}


# ---------------------------------------------------------------------------
# 4. Orchestrateur — appelé par Celery Beat chaque lundi 08h00
# ---------------------------------------------------------------------------
@shared_task(
    bind=True,
    name="reports.dispatch_weekly_report",
    queue="reports",
)
def dispatch_weekly_report(self) -> dict:
    """Génère puis envoie le rapport hebdo — orchestrateur Beat.

    Idempotent : rejoué, il ne régénère pas un rapport prêt et ne renvoie rien
    aux destinataires déjà servis.
    """
    from apps.reports.models import AutomatedReportSchedule, ReportType

    schedule = AutomatedReportSchedule.objects.filter(
        report_type=ReportType.WEEKLY, is_active=True,
    ).first()
    if not schedule:
        logger.info("[reports] aucun schedule WEEKLY actif — skip dispatch")
        return {"ok": False, "reason": "no active schedule"}

    # 1. Génération (idempotente) — l'envoi est fait ici, dans la foulée.
    generation = generate_weekly_report.apply(kwargs={"deliver": False})
    report_id = generation.result
    if generation.failed() or not isinstance(report_id, int):
        logger.error("[reports] génération hebdo en échec : %s", report_id)
        return {"ok": False, "reason": "generation failed", "error": str(report_id)}

    # 2. Envoi email + SMS aux destinataires actifs.
    return {"ok": True, **deliver_weekly_report.apply(args=[report_id]).result}


# ---------------------------------------------------------------------------
# 5. Relances, envois bloqués et rattrapage — toutes les 15 minutes
# ---------------------------------------------------------------------------
def request_retry_of_failures(report) -> int:
    """« Réessayer les échecs » : seuls les envois échoués sont relancés.

    Jamais un envoi réussi ni un envoi encore en cours. Le travail est fait par
    la tâche de relance (worker), pas pendant la requête web.
    """
    from apps.reports.models import DeliveryStatus, ReportDeliveryLog

    failed = (DeliveryStatus.FAILED, DeliveryStatus.PERMANENTLY_FAILED)
    ids = list(
        _latest_logs(report.deliveries.filter(status__in=failed))
        .values_list("pk", flat=True)
    )
    now = timezone.now()
    count = ReportDeliveryLog.objects.filter(pk__in=ids, status__in=failed).update(
        status=DeliveryStatus.RETRYING, next_retry_at=now, updated_at=now,
    )
    if count:
        try:
            retry_failed_weekly_reports.delay(report_id=report.pk)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[reports] relance non mise en file (%s) : "
                           "reprise par la tâche périodique", exc)
    return count


def _claim_retry(log_id: int):
    """Réserve un journal à relancer (un seul worker à la fois)."""
    from apps.reports.models import DeliveryStatus, ReportDeliveryLog

    with transaction.atomic():
        log = (
            ReportDeliveryLog.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("report", "recipient")
            .filter(pk=log_id, status__in=(DeliveryStatus.FAILED, DeliveryStatus.RETRYING))
            .first()
        )
        if log is None:
            return None
        log.retry_count += 1
        log.status = DeliveryStatus.QUEUED
        log.next_retry_at = None
        log.save(update_fields=["retry_count", "status", "next_retry_at", "updated_at"])
        return log


def _reconcile_stale(now) -> int:
    """Remet d'aplomb les états obsolètes (génération perdue, envoi sans issue)."""
    from apps.notifications.models import Notification, NotificationStatus
    from apps.notifications.services.errors import friendly_error
    from apps.reports.models import (
        DeliveryStatus,
        GeneratedReport,
        ReportDeliveryLog,
        ReportStatus,
    )

    fixed = GeneratedReport.objects.filter(
        status=ReportStatus.GENERATING, updated_at__lt=now - STALE_GENERATION_AFTER,
    ).update(
        status=ReportStatus.FAILED, updated_at=now,
        error_message="Génération interrompue (tâche bloquée) : relancez la génération.",
    )
    stale = ReportDeliveryLog.objects.filter(
        status=DeliveryStatus.QUEUED, updated_at__lt=now - STALE_DELIVERY_AFTER,
    )
    for log in stale:
        notif = (
            Notification.all_objects.filter(pk=log.notification_id).first()
            if log.notification_id else None
        )
        if notif is None:
            _mark_failed(log, "Envoi interrompu avant sa mise en file.", "")
        elif notif.status in (
            NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ,
        ):
            log.status = DeliveryStatus.SENT
            log.sent_at = notif.sent_at or now
            log.error_message = ""
        elif notif.status == NotificationStatus.FAILED:
            _mark_failed(log, notif.error_message, notif.error_code)
        elif notif.status == NotificationStatus.CANCELLED:
            log.status = DeliveryStatus.PERMANENTLY_FAILED
            log.error_message = (
                "Envoi annulé : " + friendly_error(notif.error_code, notif.error_message)
            )[:500]
        else:
            # En file ou en attente fournisseur (crédit épuisé) : toujours en
            # cours côté notifications, repris à la reprise du fournisseur.
            continue
        log.save()
        fixed += 1
    return fixed


def _catch_up_recent_reports(now) -> int:
    """Envoie les rapports récents aux destinataires pas encore servis."""
    from apps.reports.models import GeneratedReport, ReportStatus

    sent = 0
    recent = GeneratedReport.objects.filter(
        status=ReportStatus.READY, generated_at__gte=now - CATCH_UP_WINDOW,
    )
    for report in recent:
        for channel in ("email", "sms"):
            try:
                counts = _deliver_channel(report, channel)
            except Exception as exc:  # noqa: BLE001
                logger.exception("[reports] rattrapage %s %s : %s",
                                 report.report_code, channel, exc)
                continue
            sent += sum(v for k, v in counts.items() if k != "skipped")
    return sent


def _retry_one(log_id: int, rendered: dict) -> str:
    """Relance un journal ; retourne retried / permanent / skipped."""
    from apps.notifications.services.errors import ErrorCode, classify_error, is_retryable
    from apps.reports.models import DeliveryStatus, ReportDeliveryLog

    current = ReportDeliveryLog.objects.filter(pk=log_id).first()
    if (
        current is not None and current.status == DeliveryStatus.FAILED
        and not is_retryable(classify_error(current.error_message))
    ):
        # Ancien journal « échec » sur une erreur définitive : plus de relance
        # aveugle (le bouton « Réessayer les échecs » reste possible).
        current.status = DeliveryStatus.PERMANENTLY_FAILED
        current.next_retry_at = None
        current.save(update_fields=["status", "next_retry_at", "updated_at"])
        return "permanent"
    log = _claim_retry(log_id)
    if log is None:
        return "skipped"
    key = (log.report_id, log.channel)
    try:
        if key not in rendered:
            rendered[key] = _render_delivery(log.report, log.channel)
    except _PiiInSmsError as exc:
        _mark_failed(log, str(exc), ErrorCode.TEMPLATE_VARIABLES)
        log.save()
        return "permanent"
    body, subject = rendered[key]
    outcome = _dispatch(log, body=body, subject=subject)
    logger.info("[reports] relance %s → %s", log.destination_masked, outcome)
    return "permanent" if log.status == DeliveryStatus.PERMANENTLY_FAILED else "retried"


@shared_task(name="reports.retry_failed_weekly_reports", queue="notifications")
def retry_failed_weekly_reports(report_id: int | None = None) -> dict:
    """Relance les envois échoués dus, répare les états bloqués, rattrape l'envoi.

    - erreur temporaire : relance avec backoff 5 → 10 → 20 min, 3 fois au plus ;
    - erreur définitive (adresse, numéro, authentification, crédit SMS épuisé,
      quota) : aucune relance automatique, seulement « Réessayer les échecs » ;
    - quotas, budget et limites de débit SMS : appliqués par enqueue_notification.
    """
    from django.db.models import Q

    from apps.reports.models import DeliveryStatus, ReportDeliveryLog

    now = timezone.now()
    periodic = report_id is None
    reconciled = _reconcile_stale(now) if periodic else 0
    caught_up = _catch_up_recent_reports(now) if periodic else 0

    due = Q(status=DeliveryStatus.RETRYING) | Q(
        Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now),
        status=DeliveryStatus.FAILED,
    )
    candidates = _latest_logs(ReportDeliveryLog.objects.filter(due))
    if not periodic:
        candidates = candidates.filter(report_id=report_id)

    outcomes = {"retried": 0, "permanent": 0, "skipped": 0}
    rendered: dict = {}
    for log_id in list(candidates.values_list("pk", flat=True)):
        outcomes[_retry_one(log_id, rendered)] += 1

    result = {
        "retried": outcomes["retried"], "permanently_failed": outcomes["permanent"],
        "reconciled": reconciled, "caught_up": caught_up,
    }
    logger.info("[reports] relances : %s", result)
    return result


# ---------------------------------------------------------------------------
# 6. Purge des fichiers rapports > 90j (AC-05)
# ---------------------------------------------------------------------------
@shared_task(name="reports.cleanup_expired_report_files", queue="reports")
def cleanup_expired_report_files(days_to_keep: int = 90) -> dict:
    """Supprime les FileField PDF/Excel des rapports plus vieux que N jours.

    Ne supprime PAS la ligne GeneratedReport (on garde l'historique méta +
    summary_data), seulement les fichiers pour libérer le disque.
    """
    from apps.reports.models import GeneratedReport

    cutoff = timezone.now() - timedelta(days=days_to_keep)
    old_reports = GeneratedReport.objects.filter(
        generated_at__lt=cutoff,
    ).exclude(pdf_file="", excel_file="")

    freed_pdf, freed_excel = 0, 0
    for report in old_reports:
        if report.pdf_file:
            report.pdf_file.delete(save=False)
            freed_pdf += 1
        if report.excel_file:
            report.excel_file.delete(save=False)
            freed_excel += 1
        report.save(update_fields=["pdf_file", "excel_file", "updated_at"])

    # Rafraîchit la Gauge des destinataires (une fois par semaine suffit)
    refresh_recipients_gauge()

    logger.info("[reports] cleanup : %s PDFs + %s Excel supprimés (>%s j)",
                freed_pdf, freed_excel, days_to_keep)
    return {"freed_pdf": freed_pdf, "freed_excel": freed_excel,
            "days_to_keep": days_to_keep}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mark_failed(log, message: str, error_code: str) -> None:
    """Échec temporaire → relance avec backoff borné ; définitif → plus aucune
    relance automatique (adresse/numéro invalide, authentification, crédit
    SMS épuisé, quota…)."""
    from apps.notifications.services.errors import is_retryable
    from apps.reports.models import DeliveryStatus

    log.error_message = (message or "")[:500]
    if is_retryable(error_code) and log.retry_count < MAX_AUTO_RETRIES:
        log.status = DeliveryStatus.FAILED
        log.next_retry_at = timezone.now() + timedelta(minutes=5 * (2 ** log.retry_count))
    else:
        log.status = DeliveryStatus.PERMANENTLY_FAILED
        log.next_retry_at = None


def _apply_dispatch_result(log, result) -> str:
    """Statut du journal = résultat réel de la notification, pas sa mise en file.

    La notification asynchrone met à jour ce journal à la fin de son envoi
    (notifications.tasks). Retourne « sent », « failed » ou « queued ».
    """
    from apps.notifications.models import Notification, NotificationStatus
    from apps.notifications.services.errors import classify_error
    from apps.reports.models import DeliveryStatus

    if not result.ok:
        code = getattr(result, "error_code", "") or classify_error(result.error or "")
        _mark_failed(log, result.error or "", code)
        return "failed"
    log.provider = result.provider
    log.notification_id = result.notification_id
    notif = Notification.objects.filter(pk=result.notification_id).first()
    if notif is not None and notif.status in (
        NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ,
    ):
        log.status = DeliveryStatus.SENT
        log.sent_at = notif.sent_at or timezone.now()
        log.error_message = ""
        return "sent"
    if notif is not None and notif.status == NotificationStatus.FAILED:
        _mark_failed(log, notif.error_message, notif.error_code)
        return "failed"
    log.status = DeliveryStatus.QUEUED
    return "queued"


def _mask_email(email: str) -> str:
    """joe@example.com → j***@example.com (pour destination_masked)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"
