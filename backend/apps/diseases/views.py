from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import Disease, RiskFactor, Symptom
from .serializers import DiseaseSerializer, RiskFactorSerializer, SymptomSerializer


class DiseaseViewSet(viewsets.ModelViewSet):
    queryset = Disease.objects.prefetch_related("symptoms", "risk_factors").all()
    serializer_class = DiseaseSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "code"
    filterset_fields = ["is_active", "severity", "requires_quarantine", "requires_pass"]
    search_fields = ["name", "code", "short_name"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()


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
