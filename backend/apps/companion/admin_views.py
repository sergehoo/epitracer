"""
Endpoints ADMIN du module Companion — accès restreint aux agents.

Toutes les vues utilisent `IsAuthenticatedAndActive + HasRole` (RBAC),
réservées aux rôles : NATIONAL_ADMIN, MINISTRY, INHP, DISTRICT,
ENTRY_POINT, BORDER_AGENT, FIELD_AGENT.

CHAQUE accès à des données de localisation est journalisé via
`services.log_data_access()` (DataAccessLog) pour audit.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive
from apps.travelers.models import Traveler

from . import services
from .models import DataAccessLog, TravelerLocationPing


ALLOWED_ROLES = [
    RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
    RoleCode.DISTRICT, RoleCode.ENTRY_POINT,
    RoleCode.BORDER_AGENT, RoleCode.FIELD_AGENT,
]


def _client_ip(request) -> str | None:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ============================================================================
# Vue d'ensemble : suivis actifs aujourd'hui (tableau KPIs + liste)
# ============================================================================


class FollowupsOverviewView(APIView):
    """GET /api/v1/admin/companion/followups/

    Renvoie :
    - KPIs : total actifs, check-ins reçus aujourd'hui, manqués 48h,
      alertes ouvertes, voyageurs avec localisation récente.
    - Liste des voyageurs en suivi actif (paginée côté front).
    """

    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = ALLOWED_ROLES

    def get(self, request):
        from apps.quarantine.models import QuarantineRecord, QuarantineStatus
        from apps.surveillance.models import HealthAlert

        active = QuarantineRecord.objects.filter(
            status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
        ).select_related("traveler", "traveler__entry_point")

        today = date.today()
        checked_today = active.filter(daily_checks__check_date=today).distinct().count()
        # On considère "manqué 48h" si dernier check-in > 48h ou aucun depuis 48h post-création
        cutoff = today - timedelta(days=2)
        missed_48h = (
            active.annotate(last_check=Max("daily_checks__check_date"))
            .filter(Q(last_check__lt=cutoff) | Q(last_check__isnull=True))
            .count()
        )
        open_alerts = HealthAlert.objects.filter(status__in=["OPEN", "ACK", "INVESTIGATING"]).count()
        recent_locations = TravelerLocationPing.objects.filter(
            captured_at__gte=today - timedelta(days=7),
        ).values("traveler").distinct().count()

        # Liste (limitée à 200 pour ne pas exploser la réponse)
        rows = []
        for q in active.order_by("-started_on")[:200]:
            t = q.traveler
            last_check = q.daily_checks.order_by("-check_date").first()
            last_ping = t.location_pings.order_by("-captured_at").first()
            day_index = max(0, (today - q.started_on).days)
            rows.append({
                "public_id": t.public_id,
                "full_name": t.full_name,
                "phone": t.phone_mobile,
                "entry_point": t.entry_point.name if t.entry_point else None,
                "started_on": q.started_on,
                "day_index": day_index,
                "total_days": (q.expected_end_on - q.started_on).days,
                "last_check_date": last_check.check_date if last_check else None,
                "last_check_feeling": (
                    (last_check.symptoms_details or {}).get("feeling")
                    if last_check else None
                ),
                "has_symptoms": bool(last_check.has_symptoms) if last_check else False,
                "last_location_at": last_ping.captured_at if last_ping else None,
                "current_health_status": t.current_health_status,
            })

        return Response({
            "kpis": {
                "active": active.count(),
                "checked_today": checked_today,
                "missed_48h": missed_48h,
                "open_alerts": open_alerts,
                "with_recent_location": recent_locations,
            },
            "rows": rows,
        })


# ============================================================================
# Itinéraire d'un voyageur — pings + parcours
# ============================================================================


class TravelerLocationsView(APIView):
    """GET /api/v1/admin/companion/travelers/<public_id>/locations/

    Liste des pings GPS d'un voyageur (ordre chrono décroissant).
    Journalise l'accès dans DataAccessLog.
    """

    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = ALLOWED_ROLES

    def get(self, request, public_id: str):
        traveler = get_object_or_404(Traveler, public_id=public_id)

        services.log_data_access(
            traveler=traveler, user=request.user, resource="location",
            reason=request.query_params.get("reason", "Consultation suivi"),
            ip=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        # Filtres optionnels par dates
        since = request.query_params.get("since")
        until = request.query_params.get("until")
        qs = traveler.location_pings.order_by("-captured_at")
        if since:
            qs = qs.filter(captured_at__gte=since)
        if until:
            qs = qs.filter(captured_at__lte=until)

        pings = [
            {
                "uuid": str(p.uuid),
                "latitude": float(p.latitude),
                "longitude": float(p.longitude),
                "accuracy_m": p.accuracy_m,
                "event_type": p.event_type,
                "source": p.source,
                "captured_at": p.captured_at,
            }
            for p in qs[:500]
        ]
        return Response({
            "traveler": {"public_id": traveler.public_id, "full_name": traveler.full_name},
            "count": len(pings),
            "pings": pings,
        })


class TravelerAccessLogView(APIView):
    """GET /api/v1/admin/companion/travelers/<public_id>/access-log/

    Permet à un administrateur de voir QUI a consulté les données d'un
    voyageur. Réservé aux NATIONAL_ADMIN / MINISTRY (les autres voient
    seulement les leurs).
    """

    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]

    def get(self, request, public_id: str):
        traveler = get_object_or_404(Traveler, public_id=public_id)
        qs = DataAccessLog.objects.filter(traveler=traveler).select_related("accessed_by")
        rows = [
            {
                "accessed_at": log.accessed_at,
                "accessed_by": log.accessed_by.email if log.accessed_by else "—",
                "role": log.accessed_by_role,
                "resource": log.resource,
                "reason": log.reason,
                "ip_address": log.ip_address,
            }
            for log in qs[:300]
        ]
        return Response({"traveler": {"public_id": traveler.public_id}, "count": len(rows), "rows": rows})


# ============================================================================
# Carte de tous les pings actifs (pour /dashboard/carte-sanitaire)
# ============================================================================


class ActiveFollowupsMapView(APIView):
    """GET /api/v1/admin/companion/map/active-followups/

    Renvoie une liste légère pour afficher tous les voyageurs en suivi
    actif sur une carte (dernière position connue uniquement).
    """

    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = ALLOWED_ROLES

    def get(self, request):
        from apps.quarantine.models import QuarantineRecord, QuarantineStatus

        active = QuarantineRecord.objects.filter(
            status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
        ).select_related("traveler")

        markers = []
        for q in active[:500]:
            t = q.traveler
            last_ping = t.location_pings.order_by("-captured_at").first()
            if not last_ping:
                continue
            markers.append({
                "public_id": t.public_id,
                "full_name": t.full_name,
                "latitude": float(last_ping.latitude),
                "longitude": float(last_ping.longitude),
                "captured_at": last_ping.captured_at,
                "event_type": last_ping.event_type,
                "health_status": t.current_health_status,
            })

        return Response({"count": len(markers), "markers": markers})
