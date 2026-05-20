from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.audit.services import audit
from apps.core.permissions import HasRole, IsAuthenticatedAndActive
from apps.surveillance.services import trigger_alert

from .models import DailyCheck, FollowUpVisit, QuarantineRecord, QuarantineStatus
from .serializers import (
    DailyCheckSerializer,
    FollowUpVisitSerializer,
    QuarantineRecordSerializer,
)
from .services import close_quarantine


class QuarantineRecordViewSet(viewsets.ModelViewSet):
    queryset = (
        QuarantineRecord.objects.select_related("traveler", "disease")
        .prefetch_related("daily_checks", "visits").all()
    )
    serializer_class = QuarantineRecordSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT,
        RoleCode.FIELD_AGENT, RoleCode.OBSERVER,
    ]
    filterset_fields = ["status", "disease", "traveler"]
    search_fields = ["traveler__public_id", "traveler__last_name", "investigation_ref"]

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        qr = self.get_object()
        status_value = request.data.get("status", QuarantineStatus.COMPLETED)
        close_quarantine(qr, status=status_value)
        audit(request, action="quarantine_end", summary=f"Clôture quarantaine {qr.uuid}", target=qr)
        return Response(QuarantineRecordSerializer(qr).data)


class DailyCheckViewSet(viewsets.ModelViewSet):
    queryset = DailyCheck.objects.select_related("quarantine").all()
    serializer_class = DailyCheckSerializer
    permission_classes = [IsAuthenticatedAndActive]
    filterset_fields = ["quarantine", "has_symptoms", "alert_raised"]

    def perform_create(self, serializer):
        instance = serializer.save(reported_by_user=self.request.user)
        # Alerte si symptômes ou fièvre élevée
        if instance.has_symptoms or (instance.temperature_celsius and instance.temperature_celsius >= 38.5):
            instance.alert_raised = True
            instance.save(update_fields=["alert_raised"])
            qr = instance.quarantine
            trigger_alert(
                code="quarantine_symptoms",
                title=f"Symptômes déclarés - quarantaine {qr.uuid}",
                description=f"Voyageur {qr.traveler.public_id} a déclaré des symptômes au jour J{instance.day_index}.",
                severity="high",
                disease=qr.disease,
                target=qr,
                triggered_by=self.request.user if self.request.user.is_authenticated else None,
            )


class FollowUpVisitViewSet(viewsets.ModelViewSet):
    queryset = FollowUpVisit.objects.select_related("quarantine", "agent").all()
    serializer_class = FollowUpVisitSerializer
    permission_classes = [IsAuthenticatedAndActive]
    filterset_fields = ["quarantine", "agent", "found_person"]

    def perform_create(self, serializer):
        serializer.save(agent=self.request.user)
