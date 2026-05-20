from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import CompanionLink, Traveler, TravelHistoryEntry
from .serializers import (
    CompanionLinkSerializer,
    TravelerSerializer,
    TravelHistoryEntrySerializer,
)


class TravelerViewSet(viewsets.ModelViewSet):
    queryset = (
        Traveler.objects.select_related("nationality", "origin_country", "entry_point")
        .prefetch_related("travel_history", "companions")
        .all()
    )
    serializer_class = TravelerSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT,
        RoleCode.BORDER_AGENT, RoleCode.FIELD_AGENT, RoleCode.OBSERVER,
    ]
    lookup_field = "public_id"
    search_fields = ["public_id", "first_name", "last_name", "id_document_number", "phone", "email"]
    filterset_fields = [
        "current_health_status", "entry_point", "origin_country",
        "arrival_date", "gender", "transport_mode",
    ]

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, public_id=None):
        t = self.get_object()
        return Response({
            "public_id": t.public_id,
            "full_name": t.full_name,
            "arrival_date": t.arrival_date,
            "entry_point": t.entry_point.name if t.entry_point_id else None,
            "origin": t.origin_country.code if t.origin_country_id else None,
            "current_health_status": t.current_health_status,
        })


class TravelHistoryViewSet(viewsets.ModelViewSet):
    queryset = TravelHistoryEntry.objects.select_related("traveler", "country").all()
    serializer_class = TravelHistoryEntrySerializer
    permission_classes = [IsAuthenticatedAndActive]
    filterset_fields = ["traveler", "country", "is_transit"]


class CompanionLinkViewSet(viewsets.ModelViewSet):
    queryset = CompanionLink.objects.select_related("traveler", "companion").all()
    serializer_class = CompanionLinkSerializer
    permission_classes = [IsAuthenticatedAndActive]
    filterset_fields = ["traveler", "companion"]
