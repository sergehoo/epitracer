"""Endpoints d'agrégation pour le dashboard national."""
from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole
from apps.ebola.models import EbolaInvestigation
from apps.health_pass.models import HealthPass
from apps.quarantine.models import QuarantineRecord, QuarantineStatus
from apps.surveillance.models import HealthAlert
from apps.travelers.models import Traveler


class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        cache_key = "dashboard:overview:v1"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        data = {
            "travelers": {
                "total": Traveler.objects.count(),
                "last_24h": Traveler.objects.filter(created_at__gte=last_24h).count(),
                "by_status": dict(
                    Traveler.objects.values_list("current_health_status").annotate(c=Count("id")).values_list("current_health_status", "c")
                ),
            },
            "ebola": {
                "total": EbolaInvestigation.objects.count(),
                "by_status": dict(
                    EbolaInvestigation.objects.values_list("status").annotate(c=Count("id")).values_list("status", "c")
                ),
                "by_risk": dict(
                    EbolaInvestigation.objects.values_list("risk_level").annotate(c=Count("id")).values_list("risk_level", "c")
                ),
                "last_7d": EbolaInvestigation.objects.filter(created_at__gte=last_7d).count(),
            },
            "quarantines": {
                "active": QuarantineRecord.objects.filter(status=QuarantineStatus.ACTIVE).count(),
                "total": QuarantineRecord.objects.count(),
            },
            "passes": {
                "total": HealthPass.objects.count(),
                "active": HealthPass.objects.filter(status="active").count(),
                "revoked": HealthPass.objects.filter(status="revoked").count(),
            },
            "alerts": {
                "open": HealthAlert.objects.filter(status="open").count(),
                "critical_24h": HealthAlert.objects.filter(severity="critical", created_at__gte=last_24h).count(),
            },
            "generated_at": now.isoformat(),
        }
        cache.set(cache_key, data, timeout=30)
        return Response(data)


class EntryPointFlowsView(APIView):
    """Flux d'arrivées par point d'entrée (7 derniers jours)."""

    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        since = timezone.now().date() - timedelta(days=7)
        data = (
            Traveler.objects.filter(arrival_date__gte=since)
            .values("entry_point__name").annotate(count=Count("id")).order_by("-count")
        )
        return Response(list(data))


class HeatmapView(APIView):
    """Points GPS des confinements pour heatmap."""

    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        qs = Traveler.objects.exclude(confinement_location__isnull=True).only("confinement_location", "current_health_status")[:5000]
        return Response([
            {
                "lat": t.confinement_location.y,
                "lng": t.confinement_location.x,
                "status": t.current_health_status,
            }
            for t in qs
        ])
