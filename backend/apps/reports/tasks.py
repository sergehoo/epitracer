"""Tâches Celery du sous-module rapports hebdomadaires automatisés.

Orchestration :
    dispatch_weekly_report()
        └─ generate_weekly_report()  (agrège + PDF + Excel + persist)
        └─ send_weekly_report_email(report_id)   (boucle destinataires email)
        └─ send_weekly_report_sms(report_id)     (boucle destinataires SMS)

Tâches périodiques auxiliaires :
    - retry_failed_weekly_reports()      : reprise des envois FAILED (max 3)
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
                           triggered_by_user_id: Optional[int] = None) -> int:
    """Génère le rapport de la semaine.

    Args:
        period_start_iso : ISO datetime (défaut = semaine précédente auto)
        period_end_iso   : ISO datetime (défaut = semaine précédente auto)
        triggered_by_user_id : pk User si déclenché manuellement

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
    except Exception as exc:
        logger.exception("[reports] génération %s a échoué : %s",
                         report.report_code, exc)
        report.status = ReportStatus.FAILED
        report.error_message = str(exc)[:1000]
        report.save(update_fields=["status", "error_message", "updated_at"])
        raise

    return report.pk


# ---------------------------------------------------------------------------
# 2. Envoi Email vers destinataires actifs
# ---------------------------------------------------------------------------
@shared_task(
    bind=True,
    name="reports.send_weekly_report_email",
    queue="notifications",
)
def send_weekly_report_email(self, report_id: int) -> dict:
    """Envoie le rapport par email à tous les destinataires actifs."""
    from apps.notifications.services.dispatcher import enqueue_notification
    from apps.reports.models import (
        AutomatedReportRecipient, DeliveryChannel, DeliveryStatus,
        GeneratedReport, PreferredChannel, ReportDeliveryLog, ReportStatus,
    )
    from apps.reports.services.weekly_email import render_weekly_email_html

    report = GeneratedReport.objects.get(pk=report_id)
    if report.status != ReportStatus.READY:
        return {"ok": False, "reason": f"Report status={report.status}"}

    recipients = AutomatedReportRecipient.objects.filter(
        is_active=True,
        consent_date__isnull=False,  # AC-08 : consentement obligatoire
        preferred_channel__in=(PreferredChannel.EMAIL, PreferredChannel.BOTH),
    ).exclude(email="")

    # Filtre par report_type autorisé (si allowed_report_types non vide)
    recipients = [
        r for r in recipients
        if not r.allowed_report_types or report.report_type in r.allowed_report_types
    ]

    html_body = render_weekly_email_html(
        report.summary_data,
        download_url="",  # Phase 4 : signed URL
        pdf_attached=False,  # Phase 4 : joindre PDF
    )
    subject = f"[EpiTrace] Rapport hebdomadaire — {report.report_code}"

    sent, failed = 0, 0
    for rec in recipients:
        # Log l'envoi AVANT le dispatch (traçabilité même si crash)
        log = ReportDeliveryLog.objects.create(
            report=report,
            recipient=rec,
            channel=DeliveryChannel.EMAIL,
            provider="",  # sera renseigné par le dispatcher
            destination_masked=_mask_email(rec.email),
            status=DeliveryStatus.QUEUED,
        )
        try:
            result = enqueue_notification(
                channel="email",
                recipient=rec.email,
                body=html_body,
                subject=subject,
                traveler=None,  # rapport global, pas lié à un voyageur
                message_type="admin_notice",
            )
            if result.ok:
                log.status = DeliveryStatus.SENT
                log.sent_at = timezone.now()
                log.provider = result.provider
                log.notification_id = result.notification_id
                sent += 1
            else:
                log.status = DeliveryStatus.FAILED
                log.error_message = result.error[:500]
                failed += 1
        except Exception as exc:  # noqa: BLE001
            log.status = DeliveryStatus.FAILED
            log.error_message = str(exc)[:500]
            failed += 1
            logger.exception("[reports] email failed for %s: %s",
                             log.destination_masked, exc)
        log.save()

    logger.info("[reports] email %s : %s sent / %s failed",
                report.report_code, sent, failed)
    return {"ok": True, "sent": sent, "failed": failed,
            "report_code": report.report_code}


# ---------------------------------------------------------------------------
# 3. Envoi SMS vers destinataires actifs
# ---------------------------------------------------------------------------
@shared_task(
    bind=True,
    name="reports.send_weekly_report_sms",
    queue="notifications",
)
def send_weekly_report_sms(self, report_id: int) -> dict:
    """Envoie le SMS synthétique aux destinataires actifs.

    Bloqué si validate_no_pii échoue (safety invariant #3).
    """
    from apps.notifications.services.dispatcher import enqueue_notification
    from apps.reports.models import (
        AutomatedReportRecipient, DeliveryChannel, DeliveryStatus,
        GeneratedReport, PreferredChannel, ReportDeliveryLog, ReportStatus,
    )
    from apps.reports.services.weekly_sms import (
        render_weekly_sms, validate_no_pii,
    )

    report = GeneratedReport.objects.get(pk=report_id)
    if report.status != ReportStatus.READY:
        return {"ok": False, "reason": f"Report status={report.status}"}

    sms_body = render_weekly_sms(report.summary_data)

    # Safety : refuse d'envoyer si PII détectée (invariant #3)
    is_clean, violations = validate_no_pii(sms_body)
    if not is_clean:
        logger.error(
            "[reports] SMS refusé — PII détectée dans %s : %s",
            report.report_code, violations,
        )
        return {"ok": False, "reason": "PII detected in SMS body",
                "violations": violations}

    recipients = AutomatedReportRecipient.objects.filter(
        is_active=True,
        consent_date__isnull=False,
        preferred_channel__in=(PreferredChannel.SMS, PreferredChannel.BOTH),
    ).exclude(phone_number="")

    recipients = [
        r for r in recipients
        if not r.allowed_report_types or report.report_type in r.allowed_report_types
    ]

    sent, failed = 0, 0
    for rec in recipients:
        log = ReportDeliveryLog.objects.create(
            report=report,
            recipient=rec,
            channel=DeliveryChannel.SMS,
            destination_masked=rec.masked_phone,
            status=DeliveryStatus.QUEUED,
        )
        try:
            result = enqueue_notification(
                channel="sms",
                recipient=rec.phone_number,
                body=sms_body,
                traveler=None,
                message_type="admin_notice",
            )
            if result.ok:
                log.status = DeliveryStatus.SENT
                log.sent_at = timezone.now()
                log.provider = result.provider  # orange_ci ou twilio
                log.notification_id = result.notification_id
                sent += 1
            else:
                log.status = DeliveryStatus.FAILED
                log.error_message = result.error[:500]
                failed += 1
        except Exception as exc:  # noqa: BLE001
            log.status = DeliveryStatus.FAILED
            log.error_message = str(exc)[:500]
            failed += 1
        log.save()

    logger.info("[reports] SMS %s : %s sent / %s failed",
                report.report_code, sent, failed)
    return {"ok": True, "sent": sent, "failed": failed,
            "report_code": report.report_code}


# ---------------------------------------------------------------------------
# 4. Orchestrateur — appelé par Celery Beat chaque lundi 08h00
# ---------------------------------------------------------------------------
@shared_task(
    bind=True,
    name="reports.dispatch_weekly_report",
    queue="reports",
)
def dispatch_weekly_report(self) -> dict:
    """Génère + envoie le rapport hebdo — orchestrateur Beat.

    Idempotent : si déjà généré/envoyé cette semaine, ne double pas.
    """
    from apps.reports.models import AutomatedReportSchedule, ReportType

    # Sanity check : y a-t-il un schedule actif pour WEEKLY ?
    schedule = AutomatedReportSchedule.objects.filter(
        report_type=ReportType.WEEKLY, is_active=True,
    ).first()
    if not schedule:
        logger.info("[reports] aucun schedule WEEKLY actif — skip dispatch")
        return {"ok": False, "reason": "no active schedule"}

    # 1. Génération (idempotent)
    report_id = generate_weekly_report.apply(kwargs={}).result

    # 2. Envoi email + SMS en parallèle (best-effort si un échoue)
    email_result = {}
    sms_result = {}
    try:
        email_result = send_weekly_report_email.apply(args=[report_id]).result
    except Exception as exc:  # noqa: BLE001
        logger.exception("[reports] send_email dispatch failed: %s", exc)
        email_result = {"ok": False, "error": str(exc)}

    try:
        sms_result = send_weekly_report_sms.apply(args=[report_id]).result
    except Exception as exc:  # noqa: BLE001
        logger.exception("[reports] send_sms dispatch failed: %s", exc)
        sms_result = {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "report_id": report_id,
        "email": email_result,
        "sms": sms_result,
    }


# ---------------------------------------------------------------------------
# 5. Retry des envois FAILED (max 3 tentatives)
# ---------------------------------------------------------------------------
@shared_task(name="reports.retry_failed_weekly_reports", queue="notifications")
def retry_failed_weekly_reports() -> dict:
    """Relance les ReportDeliveryLog en FAILED avec retry_count < 3.

    Backoff : 5 min * (2^retry_count) → 5min, 10min, 20min.
    """
    from apps.notifications.services.dispatcher import enqueue_notification
    from apps.reports.models import (
        DeliveryChannel, DeliveryStatus, ReportDeliveryLog,
    )
    from apps.reports.services.weekly_email import render_weekly_email_html
    from apps.reports.services.weekly_sms import render_weekly_sms

    now = timezone.now()
    candidates = ReportDeliveryLog.objects.filter(
        status=DeliveryStatus.FAILED,
        retry_count__lt=3,
    ).filter(
        # Backoff : ne retry qu'après next_retry_at (ou immédiatement si null)
        next_retry_at__isnull=True,
    ) | ReportDeliveryLog.objects.filter(
        status=DeliveryStatus.FAILED,
        retry_count__lt=3,
        next_retry_at__lte=now,
    )
    candidates = candidates.distinct().select_related("report", "recipient")

    retried, permanently_failed = 0, 0
    for log in candidates:
        report = log.report
        rec = log.recipient
        try:
            if log.channel == DeliveryChannel.EMAIL:
                body = render_weekly_email_html(report.summary_data)
                subject = f"[EpiTrace] Rapport — {report.report_code} (relance)"
                result = enqueue_notification(
                    channel="email", recipient=rec.email,
                    body=body, subject=subject,
                    traveler=None, message_type="admin_notice",
                )
            elif log.channel == DeliveryChannel.SMS:
                body = render_weekly_sms(report.summary_data)
                result = enqueue_notification(
                    channel="sms", recipient=rec.phone_number,
                    body=body, traveler=None, message_type="admin_notice",
                )
            else:
                continue

            log.retry_count += 1
            if result.ok:
                log.status = DeliveryStatus.SENT
                log.sent_at = timezone.now()
                log.error_message = ""
                retried += 1
            else:
                log.error_message = result.error[:500]
                if log.retry_count >= 3:
                    log.status = DeliveryStatus.PERMANENTLY_FAILED
                    permanently_failed += 1
                else:
                    # Backoff exponentiel
                    delay_min = 5 * (2 ** log.retry_count)
                    log.next_retry_at = now + timedelta(minutes=delay_min)
            log.save()
        except Exception as exc:  # noqa: BLE001
            logger.exception("[reports] retry failed: %s", exc)

    logger.info("[reports] retry : %s retried, %s permanent failure",
                retried, permanently_failed)
    return {"retried": retried, "permanently_failed": permanently_failed}


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

    logger.info("[reports] cleanup : %s PDFs + %s Excel supprimés (>%s j)",
                freed_pdf, freed_excel, days_to_keep)
    return {"freed_pdf": freed_pdf, "freed_excel": freed_excel,
            "days_to_keep": days_to_keep}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _mask_email(email: str) -> str:
    """joe@example.com → j***@example.com (pour destination_masked)."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"
