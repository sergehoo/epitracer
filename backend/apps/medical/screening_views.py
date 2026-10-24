"""Revue humaine des qualifications sanitaires (agents de santé habilités).

GET  /api/v1/admin/screenings/?review_status=pending
POST /api/v1/admin/screenings/<uuid>/confirm/  {note?}  → ouvre le suivi
POST /api/v1/admin/screenings/<uuid>/dismiss/  {note}   → écarte (motif obligatoire)
"""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import HealthScreening
from .screening import confirm_screening, dismiss_screening

REVIEWER_ROLES = [
    RoleCode.NATIONAL_ADMIN,
    RoleCode.MINISTRY,
    RoleCode.INHP,
    RoleCode.DISTRICT,
    RoleCode.ENTRY_POINT,
]


class HealthScreeningSerializer(serializers.ModelSerializer):
    traveler_public_id = serializers.CharField(source="traveler.public_id", read_only=True)
    traveler_name = serializers.CharField(source="traveler.full_name", read_only=True)
    disease_code = serializers.CharField(source="disease.code", read_only=True)
    disease_name = serializers.CharField(source="disease.name", read_only=True)
    reviewed_by_email = serializers.EmailField(
        source="reviewed_by.email", read_only=True, default=None
    )
    followup_case = serializers.IntegerField(source="followup_case_id", read_only=True)

    class Meta:
        model = HealthScreening
        fields = [
            "uuid",
            "traveler_public_id",
            "traveler_name",
            "disease_code",
            "disease_name",
            "decision",
            "reasons",
            "answers",
            "followup_case",
            "review_status",
            "reviewed_by_email",
            "reviewed_at",
            "review_note",
            "created_at",
        ]
        read_only_fields = fields


class ReviewSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class HealthScreeningViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = HealthScreening.objects.select_related(
        "traveler",
        "disease",
        "reviewed_by",
    ).order_by("-created_at")
    serializer_class = HealthScreeningSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = REVIEWER_ROLES
    lookup_field = "uuid"
    filterset_fields = ["review_status", "decision", "disease__code"]
    search_fields = ["traveler__public_id", "traveler__last_name"]

    def _review(self, request, service):
        ser = ReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            screening = service(
                self.get_object(), user=request.user, note=ser.validated_data["note"]
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return Response(self.get_serializer(screening).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, uuid=None):
        return self._review(request, confirm_screening)

    @action(detail=True, methods=["post"])
    def dismiss(self, request, uuid=None):
        return self._review(request, dismiss_screening)
