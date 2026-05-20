from rest_framework import mixins, viewsets

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related("actor", "target_ct").order_by("-created_at")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
    filterset_fields = ["action", "actor", "target_id"]
    search_fields = ["summary", "ip_address"]
