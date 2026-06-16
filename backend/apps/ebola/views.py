from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.audit.services import audit
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import EbolaInvestigation
from .serializers import (
    EbolaDeclarationSerializer,
    EbolaExposureSerializer,
    EbolaInvestigationCreateSerializer,
    EbolaInvestigationSerializer,
    EbolaSymptomReportSerializer,
)
from .services import apply_risk_outcome


class EbolaInvestigationViewSet(viewsets.ModelViewSet):
    queryset = (
        EbolaInvestigation.objects.select_related("traveler", "entry_point", "investigator")
        .prefetch_related("exposure", "declaration", "symptom_reports")
        .all()
    )
    serializer_class = EbolaInvestigationSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT,
        RoleCode.BORDER_AGENT, RoleCode.FIELD_AGENT, RoleCode.OBSERVER,
    ]
    lookup_field = "case_number"
    filterset_fields = {
        "status": ["exact"],
        "risk_level": ["exact"],
        "entry_point": ["exact"],
        "traveler": ["exact"],
        # Filtrage par date d'arrivée du voyageur (range supporté)
        "traveler__arrival_date": ["exact", "gte", "lte"],
    }
    search_fields = ["case_number", "traveler__public_id", "traveler__last_name", "notes"]

    def get_serializer_class(self):
        if self.action == "create":
            return EbolaInvestigationCreateSerializer
        return EbolaInvestigationSerializer

    def perform_create(self, serializer):
        investigation = serializer.save()
        apply_risk_outcome(investigation)
        audit(
            self.request, action="create",
            summary=f"Création enquête Ebola {investigation.case_number}",
            target=investigation,
        )

    @extend_schema(request=EbolaExposureSerializer, responses=EbolaExposureSerializer)
    @action(detail=True, methods=["put", "patch"], url_path="exposure")
    def update_exposure(self, request, case_number=None):
        from .models import EbolaExposureAssessment

        inv = self.get_object()
        exposure = getattr(inv, "exposure", None)
        if exposure is None:
            ser = EbolaExposureSerializer(data=request.data)
        else:
            ser = EbolaExposureSerializer(exposure, data=request.data, partial=(request.method == "PATCH"))
        ser.is_valid(raise_exception=True)
        if exposure is None:
            EbolaExposureAssessment.objects.create(investigation=inv, **ser.validated_data)
        else:
            ser.save()
        apply_risk_outcome(inv)
        audit(request, action="update", summary=f"Mise à jour exposure {inv.case_number}", target=inv)
        return Response(EbolaExposureSerializer(inv.exposure).data)

    @extend_schema(request=EbolaSymptomReportSerializer, responses=EbolaSymptomReportSerializer)
    @action(detail=True, methods=["post"], url_path="symptoms")
    def add_symptoms(self, request, case_number=None):
        from .models import EbolaSymptomReport

        inv = self.get_object()
        ser = EbolaSymptomReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        EbolaSymptomReport.objects.create(
            investigation=inv, reported_by=request.user,
            **{k: v for k, v in ser.validated_data.items() if k != "investigation"},
        )
        apply_risk_outcome(inv)
        audit(request, action="update", summary=f"Symptômes {inv.case_number}", target=inv)
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @extend_schema(request=EbolaDeclarationSerializer, responses=EbolaDeclarationSerializer)
    @action(detail=True, methods=["put", "patch"], url_path="declaration")
    def update_declaration(self, request, case_number=None):
        from .models import EbolaDeclaration

        inv = self.get_object()
        declaration = getattr(inv, "declaration", None)
        if declaration is None:
            ser = EbolaDeclarationSerializer(data=request.data)
        else:
            ser = EbolaDeclarationSerializer(declaration, data=request.data, partial=(request.method == "PATCH"))
        ser.is_valid(raise_exception=True)
        if declaration is None:
            EbolaDeclaration.objects.create(investigation=inv, **ser.validated_data)
        else:
            ser.save()
        audit(request, action="update", summary=f"Déclaration {inv.case_number}", target=inv)
        return Response(EbolaDeclarationSerializer(inv.declaration).data)

    @extend_schema(responses=OpenApiResponse(description="Score recalculé"))
    @action(detail=True, methods=["post"], url_path="recompute-score")
    def recompute_score(self, request, case_number=None):
        inv = self.get_object()
        apply_risk_outcome(inv)
        audit(request, action="update", summary=f"Recompute score {inv.case_number}", target=inv)
        return Response({
            "case_number": inv.case_number,
            "risk_score": inv.risk_score,
            "risk_level": inv.risk_level,
            "status": inv.status,
        })

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, case_number=None):
        inv = self.get_object()
        inv.status = "closed"
        inv.save(update_fields=["status"])
        audit(request, action="update", summary=f"Clôture {inv.case_number}", target=inv)
        return Response({"detail": "Enquête clôturée."})
