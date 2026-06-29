"""Endpoints DRF du suivi médical — Phase 9B.

Préfixes :
  - `/api/v1/admin/followups/`     (auth requise, permissions par rôle)
  - `/api/v1/public/followup/`     (AllowAny + throttle mobile_followup)

Le lookup `<str:traveler_id>` accepte indifféremment un `Traveler.id`
numérique ou un `Traveler.public_id` ("TRV-XXXXXXXXXX"). Toute consultation
de données sensibles (santé, localisation) est tracée dans
`apps.companion.DataAccessLog`.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Tuple

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status as drf_status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.companion.models import DataAccessLog, TravelerLocationPing
from apps.notifications.services.dispatcher import send_manual_message
from apps.quarantine.models import (
    DailyCheck,
    DailyCheckStatus,
    QuarantineRecord,
    QuarantineStatus,
)
from apps.surveillance.services import trigger_alert
from apps.travelers.models import Traveler

from . import services_api
from .models import (
    CaseClassificationCode,
    DiseaseFollowupProtocol,
    FollowUpAction,
    FollowUpActionStatus,
    FollowUpActionType,
    LabAnalysis,
    LabAnalysisStatus,
    MedicalSample,
    MedicalSymptomReport,
    SampleTransportStatus,
    SymptomSource,
)
from .permissions import (
    CanAddLabResult,
    CanAddMedicalAction,
    CanClassifyCase,
    CanCloseFollowup,
    CanEditFollowup,
    CanRequestSample,
    CanSendFollowupNotification,
    CanViewFollowupDetail,
    CanViewLocationHistory,
    log_data_access,
)
from .serializers import (
    CaseClassificationSerializer,
    FollowUpActionSerializer,
    FollowupAssignAgentSerializer,
    FollowupCaseDetailSerializer,
    FollowupClassifySerializer,
    FollowupCloseSerializer,
    FollowupCreateActionSerializer,
    FollowupLabAnalysisCreateSerializer,
    FollowupNotifySerializer,
    FollowupRequestSampleSerializer,
    FollowupTimelineDaySerializer,
    LabAnalysisSerializer,
    MedicalSampleSerializer,
    MedicalSymptomReportSerializer,
    PublicAssistanceRequestSerializer,
    PublicFollowupStatusSerializer,
    PublicSymptomReportSerializer,
    _mask_phone,
    _public_classification_label,
)

logger = logging.getLogger("epidemitracker.medical.views")


# ============================================================================
# Helpers
# ============================================================================


def _resolve_traveler(traveler_id) -> Traveler:
    """Accepte un id entier ou un public_id (string TRV-XXX...)."""
    raw = str(traveler_id).strip()
    if not raw:
        raise Http404("traveler_id requis.")
    if raw.isdigit():
        try:
            return Traveler.objects.get(pk=int(raw))
        except Traveler.DoesNotExist:
            pass
    return get_object_or_404(Traveler, public_id=raw)


def _resolve_case(traveler_id) -> Tuple[Traveler, QuarantineRecord]:
    """Renvoie (traveler, case) — case = QuarantineRecord active/dernière.

    Raise Http404 si pas de cas associé.
    """
    traveler = _resolve_traveler(traveler_id)
    case = (
        traveler.quarantines
        .filter(status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED])
        .order_by("-started_on")
        .first()
    )
    if case is None:
        case = traveler.quarantines.order_by("-started_on").first()
    if case is None:
        raise Http404("Aucun cas de suivi pour ce voyageur.")
    return traveler, case


def _check_object_perm(request, view, case, permission_cls):
    """Évalue manuellement has_object_permission pour les APIView simples."""
    inst = permission_cls()
    if not inst.has_permission(request, view):
        raise PermissionDenied()
    has_obj = getattr(inst, "has_object_permission", None)
    if has_obj and not inst.has_object_permission(request, view, case):
        raise PermissionDenied()


# ============================================================================
# Pagination locale
# ============================================================================


class _FollowupPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


# ============================================================================
# 1. Liste des suivis
# ============================================================================


class FollowupListView(GenericAPIView):
    """GET /api/v1/admin/followups/

    Liste paginée des QuarantineRecord (filtre status, risk, disease,
    assigned_district, classification, assigned_agent, search).
    """

    permission_classes = [IsAuthenticated, CanViewFollowupDetail]
    pagination_class = _FollowupPagination
    serializer_class = None  # ne renvoie qu'un dict simple

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("risk", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("disease", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("assigned_district", int, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("classification", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("assigned_agent", int, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("search", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: dict},
        description="Liste paginée des cas de suivi médical.",
    )
    def get(self, request):
        qs = (
            QuarantineRecord.objects
            .select_related("traveler", "disease", "assigned_district", "assigned_agent")
            .order_by("-created_at")
        )
        params = request.query_params

        if status_p := params.get("status"):
            qs = qs.filter(status=status_p)
        if risk := params.get("risk"):
            qs = qs.filter(current_classification=risk)
        if disease := params.get("disease"):
            qs = qs.filter(disease__code__iexact=disease)
        if district_id := params.get("assigned_district"):
            try:
                qs = qs.filter(assigned_district_id=int(district_id))
            except ValueError:
                pass
        if classif := params.get("classification"):
            qs = qs.filter(current_classification=classif)
        if agent_id := params.get("assigned_agent"):
            try:
                qs = qs.filter(assigned_agent_id=int(agent_id))
            except ValueError:
                pass
        if search := params.get("search"):
            qs = qs.filter(
                Q(traveler__public_id__icontains=search)
                | Q(traveler__first_name__icontains=search)
                | Q(traveler__last_name__icontains=search)
            )

        page = self.paginate_queryset(qs)
        items = page if page is not None else list(qs[:200])
        today = date.today()
        results = []
        for case in items:
            day_index = max(0, (today - case.started_on).days)
            traveler = case.traveler
            results.append({
                "id": case.id,
                "uuid": str(getattr(case, "uuid", "")),
                "traveler_id": traveler.id,
                "public_id": traveler.public_id,
                "traveler_name": f"{traveler.first_name} {traveler.last_name}".strip(),
                "disease_code": case.disease.code if case.disease_id else "",
                "disease_name": case.disease.name if case.disease_id else "",
                "status": case.status,
                "current_classification": case.current_classification,
                "started_on": case.started_on,
                "expected_end_on": case.expected_end_on,
                "day_index": day_index,
                "total_days": (case.expected_end_on - case.started_on).days,
                "assigned_district": case.assigned_district.name if case.assigned_district_id else None,
                "assigned_agent_id": case.assigned_agent_id,
            })

        if page is not None:
            return self.get_paginated_response(results)
        return Response({"results": results, "count": len(results)})


# ============================================================================
# 2. Détail d'un suivi
# ============================================================================


class FollowupDetailView(APIView):
    permission_classes = [IsAuthenticated, CanViewFollowupDetail]

    @extend_schema(responses={200: FollowupCaseDetailSerializer})
    def get(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanViewFollowupDetail)

        # Pré-fetch pour économiser des requêtes.
        case = (
            QuarantineRecord.objects
            .select_related(
                "traveler", "traveler__nationality", "traveler__entry_point",
                "disease", "assigned_district", "assigned_agent",
            )
            .prefetch_related(
                "classifications",
                "samples__analyses",
                "symptom_reports",
                "daily_checks",
            )
            .get(pk=case.pk)
        )

        log_data_access(
            request=request, traveler=traveler,
            resource=DataAccessLog.Resource.HEALTH,
            reason=request.query_params.get("reason", "Consultation détail suivi"),
        )

        ser = FollowupCaseDetailSerializer(case)
        return Response(ser.data)


# ============================================================================
# 3. Timeline (DailyChecks enrichis)
# ============================================================================


class FollowupTimelineView(APIView):
    permission_classes = [IsAuthenticated, CanViewFollowupDetail]

    @extend_schema(responses={200: FollowupTimelineDaySerializer(many=True)})
    def get(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanViewFollowupDetail)

        days = (
            case.daily_checks
            .select_related("agent_responsible")
            .prefetch_related("symptom_reports", "samples", "actions")
            .order_by("day_index")
        )
        ser = FollowupTimelineDaySerializer(days, many=True)
        return Response({"results": ser.data, "count": len(ser.data)})


# ============================================================================
# 4. Création d'une FollowUpAction libre
# ============================================================================


class FollowupActionsView(APIView):
    permission_classes = [IsAuthenticated, CanAddMedicalAction]

    @extend_schema(
        request=FollowupCreateActionSerializer,
        responses={201: FollowUpActionSerializer},
    )
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanAddMedicalAction)

        ser = FollowupCreateActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        action = FollowUpAction.objects.create(
            followup_case=case,
            action_type=v["action_type"],
            title=v["title"][:200],
            description=v.get("description", ""),
            performed_by=request.user,
            status=v.get("status", FollowUpActionStatus.COMPLETED),
            metadata=v.get("metadata", {}) or {},
        )
        return Response(
            FollowUpActionSerializer(action).data,
            status=drf_status.HTTP_201_CREATED,
        )


# ============================================================================
# 5. Déclaration de symptômes par l'agent
# ============================================================================


class FollowupSymptomsView(APIView):
    permission_classes = [IsAuthenticated, CanAddMedicalAction]

    @extend_schema(
        request=MedicalSymptomReportSerializer,
        responses={201: MedicalSymptomReportSerializer},
    )
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanAddMedicalAction)

        data = request.data or {}
        symptom_code = (data.get("symptom_code") or "").strip()
        symptom_label = (data.get("symptom_label") or "").strip()
        if not symptom_code or not symptom_label:
            raise ValidationError({"symptom_code": "Requis", "symptom_label": "Requis"})

        # Auto-flag is_critical via le protocole de la maladie
        is_critical = False
        protocol = DiseaseFollowupProtocol.objects.filter(
            disease=case.disease, is_active=True,
        ).first()
        if protocol:
            criticals = set(protocol.critical_symptoms or [])
            is_critical = symptom_code in criticals

        # Lien éventuel vers un DailyCheck
        followup_day = None
        day_id = data.get("followup_day_id")
        if day_id:
            try:
                followup_day = case.daily_checks.get(pk=int(day_id))
            except (DailyCheck.DoesNotExist, ValueError):
                followup_day = None

        report = MedicalSymptomReport.objects.create(
            followup_case=case,
            followup_day=followup_day,
            symptom_code=symptom_code[:40],
            symptom_label=symptom_label[:120],
            severity=data.get("severity") or "mild",
            onset_date=data.get("onset_date") or date.today(),
            reported_by_user=request.user,
            reported_by_traveler=False,
            source=data.get("source") or SymptomSource.ADMIN,
            notes=(data.get("notes") or "")[:4000],
            is_critical=is_critical,
        )
        return Response(
            MedicalSymptomReportSerializer(report).data,
            status=drf_status.HTTP_201_CREATED,
        )


# ============================================================================
# 6. Demande de prélèvement
# ============================================================================


class FollowupSamplesView(APIView):
    permission_classes = [IsAuthenticated, CanRequestSample]

    @extend_schema(
        request=FollowupRequestSampleSerializer,
        responses={201: MedicalSampleSerializer},
    )
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanRequestSample)

        ser = FollowupRequestSampleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        # Lien éventuel vers un DailyCheck
        followup_day = None
        day_id = v.get("followup_day_id")
        if day_id:
            try:
                followup_day = case.daily_checks.get(pk=int(day_id))
            except (DailyCheck.DoesNotExist, ValueError):
                followup_day = None

        sample_code = services_api.generate_sample_code(
            disease_code=case.disease.code if case.disease_id else "DISEASE",
        )

        sample = MedicalSample.objects.create(
            followup_case=case,
            followup_day=followup_day,
            sample_code=sample_code,
            sample_type=v.get("sample_type") or "blood",
            destination_lab=v.get("destination_lab", ""),
            collection_location=v.get("collection_location", ""),
            transport_conditions=v.get("transport_conditions", ""),
            notes=v.get("notes", ""),
            transport_status=SampleTransportStatus.REQUESTED,
        )
        return Response(
            MedicalSampleSerializer(sample).data,
            status=drf_status.HTTP_201_CREATED,
        )


# ============================================================================
# 7. MAJ d'un prélèvement (PATCH)
# ============================================================================


class FollowupSampleUpdateView(APIView):
    permission_classes = [IsAuthenticated, CanRequestSample]

    @extend_schema(responses={200: MedicalSampleSerializer})
    def patch(self, request, traveler_id, sample_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanRequestSample)

        try:
            sample = MedicalSample.objects.get(pk=int(sample_id), followup_case=case)
        except (MedicalSample.DoesNotExist, ValueError):
            raise NotFound("Prélèvement introuvable.")

        updates = request.data or {}
        allowed = (
            "transport_status", "collected_at", "received_at",
            "destination_lab", "transport_conditions", "notes",
            "collection_location", "transport_departed_at",
        )
        update_fields = []
        for field in allowed:
            if field in updates:
                setattr(sample, field, updates[field])
                update_fields.append(field)

        # Si on passe à COLLECTED, on attribue collected_by + collected_at
        if updates.get("transport_status") == SampleTransportStatus.COLLECTED:
            if not sample.collected_by_id:
                sample.collected_by = request.user
                update_fields.append("collected_by")
            if not sample.collected_at:
                sample.collected_at = timezone.now()
                if "collected_at" not in update_fields:
                    update_fields.append("collected_at")

        if update_fields:
            update_fields.append("updated_at")
            sample.save(update_fields=update_fields)

        return Response(MedicalSampleSerializer(sample).data)


# ============================================================================
# 8. Création d'un résultat labo
# ============================================================================


class FollowupLabResultsView(APIView):
    permission_classes = [IsAuthenticated, CanAddLabResult]

    @extend_schema(
        request=FollowupLabAnalysisCreateSerializer,
        responses={201: LabAnalysisSerializer},
    )
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanAddLabResult)

        ser = FollowupLabAnalysisCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        try:
            sample = MedicalSample.objects.get(pk=int(v["sample_id"]), followup_case=case)
        except (MedicalSample.DoesNotExist, ValueError):
            raise ValidationError({"sample_id": "Prélèvement introuvable pour ce cas."})

        analysis = LabAnalysis.objects.create(
            sample=sample,
            lab_name=v["lab_name"],
            test_type=v["test_type"],
            result=v.get("result") or "",
            status=v.get("status") or LabAnalysisStatus.RESULT_AVAILABLE,
            notes=v.get("notes", ""),
        )
        return Response(
            LabAnalysisSerializer(analysis).data,
            status=drf_status.HTTP_201_CREATED,
        )


# ============================================================================
# 9. Validation d'une analyse
# ============================================================================


class FollowupLabValidateView(APIView):
    permission_classes = [IsAuthenticated, CanAddLabResult]

    @extend_schema(responses={200: LabAnalysisSerializer})
    def patch(self, request, traveler_id, analysis_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanAddLabResult)

        try:
            analysis = LabAnalysis.objects.select_related("sample").get(pk=int(analysis_id))
        except (LabAnalysis.DoesNotExist, ValueError):
            raise NotFound("Analyse introuvable.")
        if analysis.sample.followup_case_id != case.id:
            raise NotFound("Analyse non rattachée à ce cas.")

        analysis.validated_by = request.user
        analysis.validated_at = timezone.now()
        analysis.status = LabAnalysisStatus.VALIDATED
        analysis.save(update_fields=["validated_by", "validated_at", "status", "updated_at"])

        return Response(LabAnalysisSerializer(analysis).data)


# ============================================================================
# 10. Classification d'un cas
# ============================================================================


class FollowupClassifyView(APIView):
    permission_classes = [IsAuthenticated, CanClassifyCase]

    @extend_schema(
        request=FollowupClassifySerializer,
        responses={201: CaseClassificationSerializer},
    )
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanClassifyCase)

        ser = FollowupClassifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        new_class = services_api.update_case_classification(
            case=case,
            classification=v["classification"],
            reason=v.get("reason", ""),
            classified_by=request.user,
        )
        return Response(
            CaseClassificationSerializer(new_class).data,
            status=drf_status.HTTP_201_CREATED,
        )


# ============================================================================
# 11. Envoi d'une notification
# ============================================================================


class FollowupNotifyView(APIView):
    permission_classes = [IsAuthenticated, CanSendFollowupNotification]

    @extend_schema(request=FollowupNotifySerializer, responses={200: dict})
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanSendFollowupNotification)

        ser = FollowupNotifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        channel = v["channel"]
        result = send_manual_message(
            traveler=traveler,
            recipient=v.get("recipient") or traveler.phone_mobile or traveler.email or "",
            body=v["body"],
            subject=v.get("subject", ""),
            channel=channel,
            sent_by=request.user,
            request=request,
        )

        ok = bool(getattr(result, "ok", False))
        notif_id = getattr(result, "notification_id", None)
        error = getattr(result, "error", "")

        # Crée une FollowUpAction de traçabilité (timeline).
        masked = _mask_phone(v.get("recipient") or "")
        try:
            FollowUpAction.objects.create(
                followup_case=case,
                action_type=FollowUpActionType.NOTIFICATION_SENT,
                title=f"Notification {channel} envoyée",
                description=(
                    f"Canal : {channel}. Destinataire : {masked or '?'}. "
                    f"Statut : {'envoyée' if ok else f'échec ({error})'}."
                ),
                performed_by=request.user,
                status=FollowUpActionStatus.COMPLETED if ok else FollowUpActionStatus.CANCELLED,
                metadata={
                    "channel": channel,
                    "notification_id": notif_id,
                    "ok": ok,
                    "error": error[:200] if error else "",
                },
            )
        except Exception:  # pragma: no cover
            logger.exception("FollowUpAction NOTIFICATION_SENT creation failed")

        return Response({
            "ok": ok,
            "notification_id": notif_id,
            "channel": channel,
            "error": error,
        }, status=drf_status.HTTP_200_OK if ok else drf_status.HTTP_400_BAD_REQUEST)


# ============================================================================
# 12. Assignation agent / district / équipe
# ============================================================================


class FollowupAssignAgentView(APIView):
    permission_classes = [IsAuthenticated, CanEditFollowup]

    @extend_schema(request=FollowupAssignAgentSerializer, responses={200: dict})
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanEditFollowup)

        ser = FollowupAssignAgentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        services_api.assign_followup(
            case=case,
            assigned_agent_id=v.get("assigned_agent_id"),
            assigned_district_id=v.get("assigned_district_id"),
            assigned_team=v.get("assigned_team", "") or "",
            performed_by=request.user,
        )
        case.refresh_from_db()
        return Response({
            "ok": True,
            "assigned_agent_id": case.assigned_agent_id,
            "assigned_district_id": case.assigned_district_id,
            "assigned_team": case.assigned_team,
        })


# ============================================================================
# 13. Clôture du suivi
# ============================================================================


class FollowupCloseView(APIView):
    permission_classes = [IsAuthenticated, CanCloseFollowup]

    @extend_schema(request=FollowupCloseSerializer, responses={200: dict})
    def post(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanCloseFollowup)

        ser = FollowupCloseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data

        services_api.close_followup(
            case=case,
            closure_reason=v["closure_reason"],
            final_status=v.get("final_status", "completed"),
            notes=v.get("notes", ""),
            performed_by=request.user,
        )
        case.refresh_from_db()
        return Response({
            "ok": True,
            "status": case.status,
            "closure_reason": case.closure_reason,
            "actual_end_on": case.actual_end_on,
        })


# ============================================================================
# 14. Documents (Phase 9E)
# ============================================================================


class FollowupDocumentsView(APIView):
    """GET : liste les documents PDF disponibles pour le cas.

    POST : déclenche la génération asynchrone d'un nouveau document.
        Params query/body :
          - `type` : "sheet" | "orientation" | "sample" | "certificate"
          - `sample_id` (requis si type == "sample")
    """

    permission_classes = [IsAuthenticated, CanViewFollowupDetail]

    # Mapping document_type -> (sous-dossier MEDIA_ROOT, libellé humain)
    _DOC_FOLDERS = (
        ("certificate", "followup_certificates", "Attestation fin de suivi"),
        ("sheet", "medical/sheets", "Fiche de suivi individuelle"),
        ("sample_report", "medical/samples", "Rapport de prélèvement"),
        ("orientation", "medical/orientations", "Fiche d'orientation médicale"),
    )

    def _list_documents(self, case):
        """Inspecte MEDIA_ROOT et renvoie les documents existants pour ce cas."""
        from django.conf import settings
        from django.core.files.storage import default_storage
        from pathlib import Path

        from .models import FollowUpAction, FollowUpActionType

        media_root = Path(getattr(settings, "MEDIA_ROOT", ""))
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        case_uuid = str(case.uuid)
        results = []

        # 1) Documents liés directement à l'UUID du cas
        for doc_type, folder, label in self._DOC_FOLDERS:
            folder_path = media_root / folder
            if not folder_path.exists():
                continue
            for p in sorted(folder_path.glob("*.pdf")):
                if case_uuid not in p.name and doc_type != "sample_report":
                    continue
                try:
                    stat = p.stat()
                except OSError:
                    continue
                rel = str(p.relative_to(media_root))
                results.append({
                    "id": f"{doc_type}:{p.name}",
                    "type": doc_type,
                    "label": label,
                    "filename": p.name,
                    "url": media_url + rel,
                    "generated_at": timezone.datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.get_current_timezone(),
                    ).isoformat(),
                    "size_bytes": stat.st_size,
                })

        # 2) Documents prélèvements : on filtre via les sample_codes du cas
        sample_codes = list(
            MedicalSample.objects
            .filter(followup_case=case)
            .values_list("sample_code", flat=True)
        )
        # Filtrer la liste pré-construite pour ne garder que les samples du cas
        filtered = []
        for doc in results:
            if doc["type"] != "sample_report":
                filtered.append(doc); continue
            # Le filename est dérivé du sample_code (cf _sample_report_relative_path)
            stem = doc["filename"].removesuffix(".pdf")
            if any(stem == _sanitize_code(c) for c in sample_codes):
                filtered.append(doc)
        results = filtered

        # 3) Enrichissement : générateur (lecture FollowUpAction metadata)
        action_qs = (
            FollowUpAction.objects
            .filter(
                followup_case=case,
                metadata__kind="document_generated",
            )
            .select_related("performed_by")
            .order_by("-performed_at")
        )
        path_to_actor = {}
        for a in action_qs:
            p = a.metadata.get("path") if isinstance(a.metadata, dict) else None
            if not p:
                continue
            actor = a.performed_by
            path_to_actor[p] = {
                "actor_id": actor.id if actor else None,
                "actor_name": (
                    (actor.get_full_name() or actor.email)
                    if actor else "Système"
                ),
            }
        for doc in results:
            actor = path_to_actor.get(doc["url"].replace(media_url, "", 1))
            doc["generated_by"] = actor or {"actor_id": None, "actor_name": "—"}

        results.sort(key=lambda d: d.get("generated_at") or "", reverse=True)
        return results

    @extend_schema(responses={200: dict})
    def get(self, request, traveler_id):
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanViewFollowupDetail)
        return Response({
            "documents": self._list_documents(case),
            "available_types": [
                {"code": t, "label": label}
                for t, _f, label in self._DOC_FOLDERS
            ],
        })

    @extend_schema(
        parameters=[
            OpenApiParameter("type", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("sample_id", int, OpenApiParameter.QUERY, required=False),
        ],
        responses={202: dict, 400: dict},
    )
    def post(self, request, traveler_id):
        """Déclenche la génération asynchrone d'un document."""
        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanViewFollowupDetail)

        doc_type = (
            request.query_params.get("type")
            or request.data.get("type")
            or ""
        ).strip().lower()

        from .tasks import (
            generate_followup_completion_certificate,
            generate_followup_individual_sheet,
            generate_medical_orientation_form_task,
            generate_sample_collection_report_task,
        )

        agent_id = getattr(request.user, "id", None)

        if doc_type in ("sheet", "individual_sheet"):
            task = generate_followup_individual_sheet
            args = (case.pk,)
            kwargs = {}
        elif doc_type == "orientation":
            task = generate_medical_orientation_form_task
            args = (case.pk,)
            kwargs = {"agent_id": agent_id}
        elif doc_type in ("sample", "sample_report"):
            sample_id = (
                request.query_params.get("sample_id")
                or request.data.get("sample_id")
            )
            if not sample_id:
                return Response(
                    {"detail": "sample_id requis pour type=sample."},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
            try:
                sample_id = int(sample_id)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "sample_id invalide."},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
            if not MedicalSample.objects.filter(
                pk=sample_id, followup_case=case,
            ).exists():
                return Response(
                    {"detail": "Prélèvement introuvable pour ce cas."},
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
            task = generate_sample_collection_report_task
            args = (sample_id,)
            kwargs = {}
        elif doc_type == "certificate":
            task = generate_followup_completion_certificate
            args = (case.pk,)
            kwargs = {}
        else:
            return Response(
                {"detail": (
                    "type invalide. Attendu : "
                    "sheet | orientation | sample | certificate."
                )},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        # Tentative async ; en dev/sync fallback exécution immédiate
        job_id = None
        try:
            async_res = task.delay(*args, **kwargs)
            job_id = getattr(async_res, "id", None)
        except Exception:
            logger.exception("Enqueue Celery KO — fallback sync exec")
            try:
                task.run(*args, **kwargs)
            except Exception:
                logger.exception("Exécution synchrone KO")
                return Response(
                    {"detail": "Génération du document indisponible."},
                    status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {
                "queued": True,
                "type": doc_type,
                "job_id": job_id,
                "note": (
                    "La génération est asynchrone — le document apparaîtra "
                    "dans GET /documents/ dès qu'il sera prêt."
                ),
            },
            status=drf_status.HTTP_202_ACCEPTED,
        )


def _sanitize_code(code: str) -> str:
    """Reproduit la sanitization de tasks._sample_report_relative_path."""
    import re as _re
    return _re.sub(r"[^A-Za-z0-9_-]", "_", code or "")


# ============================================================================
# 15. Audit (FollowUpAction + DataAccessLog)
# ============================================================================


class FollowupAuditView(APIView):
    """Vue audit unifiée — exige `?reason=` pour traçabilité RGPD."""

    permission_classes = [IsAuthenticated, CanViewFollowupDetail]

    @extend_schema(
        parameters=[
            OpenApiParameter("reason", str, OpenApiParameter.QUERY, required=True),
        ],
        responses={200: dict},
    )
    def get(self, request, traveler_id):
        reason = (request.query_params.get("reason") or "").strip()
        if not reason:
            return Response(
                {"detail": "Reason required for sensitive data access."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanViewFollowupDetail)

        actions = list(
            FollowUpAction.objects
            .filter(followup_case=case)
            .select_related("performed_by")
            .order_by("-performed_at")[:200]
        )
        accesses = list(
            DataAccessLog.objects
            .filter(traveler=traveler)
            .select_related("accessed_by")
            .order_by("-accessed_at")[:200]
        )

        unified = []
        for a in actions:
            actor = a.performed_by
            unified.append({
                "type": "action",
                "id": a.id,
                "timestamp": a.performed_at,
                "actor_id": actor.id if actor else None,
                "actor_name": (actor.get_full_name() or actor.email) if actor else "Système",
                "label": a.title,
                "details": {
                    "action_type": a.action_type,
                    "status": a.status,
                    "description": a.description,
                    "metadata": a.metadata,
                },
            })
        for log in accesses:
            actor = log.accessed_by
            unified.append({
                "type": "access",
                "id": log.id,
                "timestamp": log.accessed_at,
                "actor_id": actor.id if actor else None,
                "actor_name": (actor.get_full_name() or actor.email) if actor else "Système",
                "label": f"Accès {log.resource}",
                "details": {
                    "resource": log.resource,
                    "reason": log.reason,
                    "role": log.accessed_by_role,
                    "ip_address": log.ip_address,
                },
            })
        unified.sort(key=lambda x: x["timestamp"] or timezone.now(), reverse=True)

        # Trace cette consultation comme un access sensible
        log_data_access(
            request=request, traveler=traveler,
            resource=DataAccessLog.Resource.FULL_PROFILE,
            reason=reason,
        )

        return Response({
            "results": unified,
            "count": len(unified),
            "reason": reason,
        })


# ============================================================================
# 16. Historique de localisation (sensible)
# ============================================================================


class FollowupLocationHistoryView(APIView):
    permission_classes = [IsAuthenticated, CanViewLocationHistory]

    @extend_schema(
        parameters=[OpenApiParameter("reason", str, OpenApiParameter.QUERY, required=True)],
        responses={200: dict},
    )
    def get(self, request, traveler_id):
        reason = (request.query_params.get("reason") or "").strip()
        if not reason:
            return Response(
                {"detail": "Reason required for sensitive data access."},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        traveler, case = _resolve_case(traveler_id)
        _check_object_perm(request, self, case, CanViewLocationHistory)

        pings = (
            TravelerLocationPing.objects
            .filter(traveler=traveler)
            .order_by("-captured_at")[:50]
        )
        log_data_access(
            request=request, traveler=traveler,
            resource=DataAccessLog.Resource.LOCATION,
            reason=reason,
        )

        return Response({
            "results": [
                {
                    "id": p.id,
                    "latitude": float(p.latitude),
                    "longitude": float(p.longitude),
                    "accuracy_m": p.accuracy_m,
                    "event_type": p.event_type,
                    "captured_at": p.captured_at,
                    "consent_version": p.consent_version,
                }
                for p in pings
            ],
            "count": pings.count() if hasattr(pings, "count") else len(pings),
        })


# ============================================================================
# Endpoints PUBLICS — AllowAny + ScopedRateThrottle "mobile_followup"
# ============================================================================


class PublicFollowupStatusView(APIView):
    """GET /api/v1/public/followup/status/?public_id=TRV-XXX

    Aucune PII en clair — adapté à la PWA / app mobile voyageur.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_followup"

    @extend_schema(
        parameters=[OpenApiParameter("public_id", str, OpenApiParameter.QUERY, required=True)],
        responses={200: PublicFollowupStatusSerializer},
    )
    def get(self, request):
        public_id = (request.query_params.get("public_id") or "").strip()
        if not public_id:
            return Response({"detail": "public_id requis."}, status=400)
        try:
            traveler, case = _resolve_case(public_id)
        except Http404:
            return Response({"detail": "Aucun suivi trouvé."}, status=404)

        today = date.today()
        day_index = max(0, (today - case.started_on).days)
        total_days = max(1, (case.expected_end_on - case.started_on).days)
        days_completed = case.daily_checks.filter(status=DailyCheckStatus.COMPLETED).count()
        days_remaining = max(0, total_days - day_index)

        last_check = case.daily_checks.order_by("-check_date").first()
        feeling = ""
        if last_check and last_check.symptoms_details:
            feeling = (last_check.symptoms_details or {}).get("feeling", "") or ""

        payload = {
            "public_id": traveler.public_id,
            "disease_code": case.disease.code if case.disease_id else "",
            "disease_name": case.disease.name if case.disease_id else "",
            "status": case.status,
            "started_on": case.started_on,
            "expected_end_on": case.expected_end_on,
            "day_index": day_index,
            "total_days": total_days,
            "current_classification_label": _public_classification_label(case.current_classification),
            "last_checkin_date": last_check.check_date if last_check else None,
            "last_checkin_feeling": feeling,
            "days_completed": days_completed,
            "days_remaining": days_remaining,
            "assistance_phones": {
                "samu": "185",
                "allo_sante": "143",
                "secours": "101",
            },
        }
        return Response(PublicFollowupStatusSerializer(payload).data)


class PublicSymptomReportView(APIView):
    """POST /api/v1/public/followup/symptoms/"""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_followup"

    @extend_schema(
        request=PublicSymptomReportSerializer,
        responses={201: MedicalSymptomReportSerializer},
    )
    def post(self, request):
        ser = PublicSymptomReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            traveler, case = _resolve_case(v["public_id"])
        except Http404:
            return Response({"detail": "Suivi introuvable."}, status=404)

        is_critical = False
        protocol = DiseaseFollowupProtocol.objects.filter(
            disease=case.disease, is_active=True,
        ).first()
        if protocol:
            is_critical = v["symptom_code"] in set(protocol.critical_symptoms or [])

        report = MedicalSymptomReport.objects.create(
            followup_case=case,
            symptom_code=v["symptom_code"][:40],
            symptom_label=v["symptom_label"][:120],
            severity=v.get("severity", "mild"),
            onset_date=v.get("onset_date") or date.today(),
            reported_by_traveler=True,
            source=SymptomSource.CHECKIN,
            notes=v.get("notes", ""),
            is_critical=is_critical,
        )
        return Response(
            MedicalSymptomReportSerializer(report).data,
            status=drf_status.HTTP_201_CREATED,
        )


class PublicAssistanceView(APIView):
    """POST /api/v1/public/followup/assistance/

    Crée une FollowUpAction "demande d'assistance" + alerte si urgence.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_followup"

    @extend_schema(request=PublicAssistanceRequestSerializer, responses={201: dict})
    def post(self, request):
        ser = PublicAssistanceRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        try:
            traveler, case = _resolve_case(v["public_id"])
        except Http404:
            return Response({"detail": "Suivi introuvable."}, status=404)

        is_emergency = bool(v.get("is_emergency"))
        action = FollowUpAction.objects.create(
            followup_case=case,
            action_type=FollowUpActionType.CONTACTED,
            title="Demande d'assistance voyageur",
            description=(v.get("reason") or "")[:2000],
            status=FollowUpActionStatus.PLANNED if not is_emergency else FollowUpActionStatus.IN_PROGRESS,
            metadata={
                "channel": "public_api",
                "is_emergency": is_emergency,
                "latitude": v.get("latitude"),
                "longitude": v.get("longitude"),
            },
        )

        alert = None
        if is_emergency:
            try:
                alert = trigger_alert(
                    code="followup_traveler_assistance",
                    title="SOS voyageur",
                    description=(v.get("reason") or "")[:500],
                    severity="high",
                    disease=case.disease,
                    target=case,
                    metadata={
                        "traveler_public_id": traveler.public_id,
                        "latitude": v.get("latitude"),
                        "longitude": v.get("longitude"),
                    },
                )
            except Exception:  # pragma: no cover
                logger.exception("trigger_alert failed for assistance request")

        return Response({
            "ok": True,
            "action_id": action.id,
            "alert_created": alert is not None,
            "message": (
                "Demande reçue. Une équipe sanitaire prendra contact rapidement."
                if not is_emergency else
                "Demande d'urgence transmise. Composez le 143 (Allô Santé) ou le 185 (SAMU)."
            ),
        }, status=drf_status.HTTP_201_CREATED)
