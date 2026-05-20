from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import Country, EntryPoint, HealthZone
from .serializers import CountrySerializer, EntryPointSerializer, HealthZoneSerializer


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all().order_by("name")
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["code", "code3", "name", "region"]
    filterset_fields = ["region", "risk_level"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY]
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()


class EntryPointViewSet(viewsets.ModelViewSet):
    queryset = EntryPoint.objects.select_related("country").all().order_by("name")
    serializer_class = EntryPointSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["code", "name", "city", "country__name", "iata_code"]
    filterset_fields = ["type", "country", "is_active"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()


class HealthZoneViewSet(viewsets.ModelViewSet):
    queryset = HealthZone.objects.all().order_by("level", "name")
    serializer_class = HealthZoneSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["level", "risk_level", "parent"]
    search_fields = ["code", "name"]
