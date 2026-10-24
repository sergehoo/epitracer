from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import Disease, RiskFactor, Symptom
from .serializers import DiseaseSerializer, RiskFactorSerializer, SymptomSerializer


class DiseaseViewSet(viewsets.ModelViewSet):
    queryset = Disease.objects.prefetch_related("symptoms", "risk_factors").all()
    serializer_class = DiseaseSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "code"
    filterset_fields = [
        "is_active",
        "severity",
        "requires_quarantine",
        "requires_pass",
        "is_published",
    ]
    search_fields = ["name", "code", "short_name"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy", "publish", "unpublish"}:
            self.required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def publish(self, request, code=None):
        """Publie la fiche sur le portail (administrateur habilité, contenu requis)."""
        from apps.portal.services import publish_disease
        from apps.portal.views import run_service

        disease = run_service(publish_disease, self.get_object(), request.user)
        return Response(self.get_serializer(disease).data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, code=None):
        from apps.portal.services import unpublish_disease
        from apps.portal.views import run_service

        disease = run_service(unpublish_disease, self.get_object(), request.user)
        return Response(self.get_serializer(disease).data)


class SymptomViewSet(viewsets.ModelViewSet):
    queryset = Symptom.objects.select_related("disease").all()
    serializer_class = SymptomSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
    filterset_fields = ["disease", "is_red_flag"]


class RiskFactorViewSet(viewsets.ModelViewSet):
    queryset = RiskFactor.objects.select_related("disease").all()
    serializer_class = RiskFactorSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
    filterset_fields = ["disease"]
