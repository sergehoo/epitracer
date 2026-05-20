from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import HealthAlert
from .serializers import HealthAlertSerializer


class HealthAlertViewSet(viewsets.ModelViewSet):
    queryset = HealthAlert.objects.select_related("disease", "entry_point", "zone", "triggered_by").all()
    serializer_class = HealthAlertSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]
    filterset_fields = ["severity", "status", "disease", "entry_point", "zone"]
    search_fields = ["code", "title", "description"]

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.status = "ack"
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=["status", "acknowledged_by", "acknowledged_at"])
        return Response(HealthAlertSerializer(alert).data)
