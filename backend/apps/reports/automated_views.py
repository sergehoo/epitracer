"""ViewSets DRF pour les rapports hebdomadaires automatisés.

13 endpoints exposés (préfixés /api/v1/reports/) :

    GET    /weekly/                          → liste paginée
    POST   /weekly/generate/                 → génération manuelle
    GET    /weekly/{id}/                     → détail
    GET    /weekly/{id}/download/            → signed URL PDF/Excel
    POST   /weekly/{id}/send/                → envoi manuel
    GET    /recipients/                      → liste destinataires
    POST   /recipients/                      → ajouter
    PATCH  /recipients/{id}/                 → modifier
    DELETE /recipients/{id}/                 → soft-delete
    POST   /recipients/{id}/test/            → envoi test
    POST   /recipients/import-csv/           → import bulk
    GET    /recipients/export-csv/           → export bulk
    GET    /schedule/                        → config Beat
    PATCH  /schedule/                        → modifier Beat
    GET    /delivery-logs/                   → historique envois

Signed URL download : token éphémère (7 jours) via django.core.signing.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta

from django.core import signing
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import (
    AutomatedReportRecipient, AutomatedReportSchedule, DeliveryStatus,
    GeneratedReport, ReportDeliveryLog, ReportType,
)
from .permissions import (
    CanDownloadReports, CanGenerateWeeklyReports, CanManageReportRecipients,
    CanManageReportSchedule, CanSendWeeklyReports, CanViewWeeklyReports,
)
from .serializers import (
    AutomatedReportRecipientLightSerializer,
    AutomatedReportRecipientSerializer, AutomatedReportScheduleSerializer,
    GenerateReportInputSerializer, GeneratedReportDetailSerializer,
    GeneratedReportLightSerializer, RecipientImportCsvInputSerializer,
    ReportDeliveryLogSerializer, TestSendInputSerializer,
)

logger = logging.getLogger("epidemitracker.reports.views")


SIGN_SALT = "reports.weekly.download"
DOWNLOAD_TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 jours


# ============================================================================
# 1. GeneratedReport — liste, détail, générer, envoyer, download
# ============================================================================
class WeeklyReportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """CRUD lecture + actions (generate/send/download) sur GeneratedReport."""
    queryset = GeneratedReport.objects.all()
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action in ("retrieve", "generate"):
            return GeneratedReportDetailSerializer
        return GeneratedReportLightSerializer

    def get_permissions(self):
        if self.action == "generate":
            return [CanGenerateWeeklyReports()]
        if self.action == "send":
            return [CanSendWeeklyReports()]
        if self.action == "download":
            return [CanDownloadReports()]
        return [CanViewWeeklyReports()]

    def get_queryset(self):
        qs = super().get_queryset().order_by("-period_start")
        # Filtres optionnels
        report_type = self.request.query_params.get("report_type")
        if report_type:
            qs = qs.filter(report_type=report_type)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    # ------------------------------------------------------------------ generate
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """POST /weekly/generate/ — déclencher une génération manuelle.

        Retourne 202 Accepted avec l'ID du rapport (peut être encore PENDING
        si Celery est en asynchrone).
        """
        from .tasks import generate_weekly_report

        input_ser = GenerateReportInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        kwargs = {"triggered_by_user_id": request.user.pk}
        if data.get("period_start") and data.get("period_end"):
            kwargs["period_start_iso"] = data["period_start"].isoformat()
            kwargs["period_end_iso"] = data["period_end"].isoformat()

        # Utilise apply() en synchrone pour renvoyer le report_id
        # (le task est idempotent — safe même s'il tourne en concurrent)
        try:
            report_id = generate_weekly_report.apply(kwargs=kwargs).result
        except Exception as exc:  # noqa: BLE001
            logger.exception("Manual generate failed: %s", exc)
            return Response(
                {"detail": f"Génération échouée : {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        report = GeneratedReport.objects.get(pk=report_id)
        return Response(
            GeneratedReportDetailSerializer(report).data,
            status=status.HTTP_202_ACCEPTED,
        )

    # -------------------------------------------------------------------- send
    @action(detail=True, methods=["post"], url_path="send")
    def send(self, request, pk=None):
        """POST /weekly/{id}/send/ — déclencher un envoi manuel."""
        from .tasks import send_weekly_report_email, send_weekly_report_sms

        report = self.get_object()
        channels = request.data.get("channels", ["email", "sms"])

        results = {}
        if "email" in channels:
            results["email"] = send_weekly_report_email.apply(args=[report.pk]).result
        if "sms" in channels:
            results["sms"] = send_weekly_report_sms.apply(args=[report.pk]).result

        return Response({"ok": True, "report_id": report.pk, **results})

    # ---------------------------------------------------------------- download
    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        """GET /weekly/{id}/download/?format=pdf|xlsx

        Retourne un fichier signé + tracé.
        """
        report = self.get_object()
        fmt = (request.query_params.get("format") or "pdf").lower()
        if fmt == "pdf":
            f = report.pdf_file
        elif fmt in ("xlsx", "excel", "csv"):
            f = report.excel_file
        else:
            return Response(
                {"detail": "format doit être 'pdf' ou 'xlsx'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not f:
            return Response(
                {"detail": f"Fichier {fmt} non disponible pour ce rapport."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Audit trail : trace l'IP + user-agent (AC-07 défense en profondeur)
        try:
            from apps.audit.models import AuditLog
            from django.contrib.contenttypes.models import ContentType
            AuditLog.objects.create(
                actor=request.user if request.user.is_authenticated else None,
                action="reports.weekly.download",
                summary=f"Download {fmt} de {report.report_code}",
                target_ct=ContentType.objects.get_for_model(GeneratedReport),
                target_id=report.pk,
                payload={"format": fmt, "report_code": report.report_code},
                ip_address=_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:400],
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Audit log download failed: %s", exc)

        response = FileResponse(f.open("rb"), as_attachment=True,
                                filename=f.name.split("/")[-1])
        response["X-Robots-Tag"] = "noindex, nofollow"  # non indexable
        return response

    # ------------------------------------------------------ signed_download_url
    @action(detail=True, methods=["get"], url_path="signed-url")
    def signed_download_url(self, request, pk=None):
        """GET /weekly/{id}/signed-url/?format=pdf → URL signée 7j."""
        report = self.get_object()
        fmt = (request.query_params.get("format") or "pdf").lower()
        if fmt not in ("pdf", "xlsx"):
            return Response({"detail": "format invalide"}, status=400)

        token = signing.dumps(
            {"report_id": report.pk, "format": fmt, "issued_to": request.user.pk},
            salt=SIGN_SALT,
        )
        return Response({
            "token": token,
            "url": f"/api/v1/reports/weekly/signed-download/?token={token}",
            "expires_in_seconds": DOWNLOAD_TOKEN_TTL_SECONDS,
        })


# ============================================================================
# 2. AutomatedReportRecipient — CRUD complet + actions
# ============================================================================
class ReportRecipientViewSet(viewsets.ModelViewSet):
    """CRUD des destinataires + import/export CSV + test-envoi."""
    queryset = AutomatedReportRecipient.objects.all()
    parser_classes = (MultiPartParser, FormParser)

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewWeeklyReports()]
        return [CanManageReportRecipients()]

    def get_serializer_class(self):
        if self.action == "list":
            return AutomatedReportRecipientLightSerializer
        return AutomatedReportRecipientSerializer

    def get_queryset(self):
        qs = super().get_queryset().select_related("district")
        # Filtres
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                full_name__icontains=q,
            ) | qs.filter(email__icontains=q) | qs.filter(organization__icontains=q)
        for param in ("preferred_channel", "language", "is_active"):
            val = self.request.query_params.get(param)
            if val is not None and val != "":
                if param == "is_active":
                    qs = qs.filter(is_active=val.lower() in ("1", "true", "yes"))
                else:
                    qs = qs.filter(**{param: val})
        district = self.request.query_params.get("district")
        if district:
            qs = qs.filter(district_id=district)
        return qs.distinct().order_by("full_name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        """Soft-delete : is_active=False + soft_delete du BaseModel."""
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        try:
            instance.delete()  # soft-delete via SoftDeleteModel du BaseModel
        except TypeError:
            # Si delete() a été surchargé sans arg
            pass

    # ---------------------------------------------------------------- test-send
    @action(detail=True, methods=["post"], url_path="test")
    def test_send(self, request, pk=None):
        """POST /recipients/{id}/test/ — envoie un message test au destinataire.

        Le message est **préfixé [TEST]** pour éviter la confusion (AC-09).
        """
        from apps.notifications.services.dispatcher import enqueue_notification

        rec = self.get_object()
        input_ser = TestSendInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        channel = input_ser.validated_data["channel"]

        body = (
            "[TEST] Ceci est un message de test EpiTrace envoyé par "
            f"{request.user.email or request.user.username}. Aucune action requise."
        )
        recipient = rec.email if channel == "email" else rec.phone_number
        if not recipient:
            return Response(
                {"detail": f"Destinataire sans {channel}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = enqueue_notification(
            channel=channel,
            recipient=recipient,
            body=body,
            subject="[TEST] EpiTrace — Test d'envoi" if channel == "email" else "",
            traveler=None,
            message_type="admin_notice",
            sent_by=request.user,
            request=request,
        )
        if result.ok:
            return Response({
                "ok": True,
                "notification_id": result.notification_id,
                "provider": result.provider,
            })
        return Response(
            {"ok": False, "error": result.error},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ---------------------------------------------------------------- import CSV
    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        """POST /recipients/import-csv/ — import bulk depuis un CSV.

        Format attendu (entêtes en 1ère ligne, séparateur , ou ;) :
            full_name;email;phone_number;organization;preferred_channel;consent_date

        Le `dry_run=true` retourne le rapport sans écrire en base.
        """
        input_ser = RecipientImportCsvInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        csv_file = input_ser.validated_data["csv_file"]
        dry_run = input_ser.validated_data["dry_run"]

        # Lit avec detect du séparateur (, ou ;)
        raw = csv_file.read().decode("utf-8-sig", errors="replace")
        sample = raw[:1024]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(raw), dialect=dialect)

        created, skipped, errors = 0, 0, []
        for i, row in enumerate(reader, start=2):
            try:
                full_name = (row.get("full_name") or "").strip()
                if not full_name:
                    skipped += 1
                    errors.append({"line": i, "error": "full_name manquant"})
                    continue
                defaults = {
                    "job_title": (row.get("job_title") or "").strip(),
                    "organization": (row.get("organization") or "").strip(),
                    "phone_number": (row.get("phone_number") or "").strip(),
                    "email": (row.get("email") or "").strip(),
                    "preferred_channel": (row.get("preferred_channel") or "email").strip().lower(),
                    "language": (row.get("language") or "fr").strip(),
                    "consent_date": (row.get("consent_date") or None) or None,
                    "consent_evidence": (row.get("consent_evidence") or "").strip(),
                    "is_active": True,
                    "created_by": request.user,
                }
                if not dry_run:
                    AutomatedReportRecipient.objects.update_or_create(
                        full_name=full_name,
                        email=defaults["email"] or "",
                        defaults=defaults,
                    )
                created += 1
            except Exception as exc:  # noqa: BLE001
                skipped += 1
                errors.append({"line": i, "error": str(exc)[:200]})

        return Response({
            "ok": True,
            "dry_run": dry_run,
            "created_or_updated": created,
            "skipped": skipped,
            "errors": errors[:50],
        })

    # ---------------------------------------------------------------- export CSV
    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        """GET /recipients/export-csv/ — export CSV UTF-8 BOM."""
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "full_name", "job_title", "organization",
            "phone_number", "email", "preferred_channel",
            "language", "district", "is_active", "consent_date",
        ])
        for rec in self.get_queryset():
            writer.writerow([
                rec.full_name, rec.job_title, rec.organization,
                rec.phone_number, rec.email, rec.preferred_channel,
                rec.language,
                (rec.district.name if rec.district_id else ""),
                "1" if rec.is_active else "0",
                (rec.consent_date.isoformat() if rec.consent_date else ""),
            ])
        response = HttpResponse(
            "﻿" + buf.getvalue(),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="report-recipients.csv"'
        return response


# ============================================================================
# 3. AutomatedReportSchedule — singleton (1 seul actif par type)
# ============================================================================
class ReportScheduleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """GET liste + GET/PATCH sur le schedule courant (WEEKLY par défaut)."""
    queryset = AutomatedReportSchedule.objects.all()
    serializer_class = AutomatedReportScheduleSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [CanViewWeeklyReports()]
        return [CanManageReportSchedule()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


# ============================================================================
# 4. ReportDeliveryLog — historique read-only
# ============================================================================
class ReportDeliveryLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Historique des envois — read-only, filtres par report/status/channel."""
    queryset = ReportDeliveryLog.objects.all()
    serializer_class = ReportDeliveryLogSerializer
    permission_classes = [CanViewWeeklyReports]

    def get_queryset(self):
        qs = super().get_queryset().select_related("report", "recipient")
        for param in ("report", "recipient", "channel", "status", "provider"):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        return qs.order_by("-created_at")


# ============================================================================
# Helpers
# ============================================================================
def _client_ip(request) -> str:
    """Extrait l'IP client en respectant X-Forwarded-For (Traefik)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
