from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import Notification, NotificationTemplate
from .serializers import NotificationSerializer, NotificationTemplateSerializer
from .tasks import send_notification


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all().order_by("code")
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
    search_fields = ["code", "name"]
    filterset_fields = ["is_active"]


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.select_related("template").all().order_by("-created_at")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP, RoleCode.DISTRICT]
    filterset_fields = ["channel", "status", "template"]

    @action(detail=False, methods=["post"], url_path="send")
    def send_now(self, request):
        send_notification.delay(
            channel=request.data["channel"],
            recipient=request.data["recipient"],
            template_code=request.data.get("template_code"),
            subject=request.data.get("subject", ""),
            body=request.data.get("body", ""),
            context=request.data.get("context", {}),
        )
        return Response({"queued": True})
