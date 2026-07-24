"""URLs du centre de rapports.

Deux blocs distincts :
  - endpoints d'export à la volée (legacy) : /types/, /travelers/, /alerts/, ...
  - endpoints des rapports automatisés (Phase 4) : /weekly/, /recipients/, ...

Le signed-download est aussi exposé au niveau top pour ne pas nécessiter
d'ID (le token contient l'ID).
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .automated_views import (
    ReportDeliveryLogViewSet, ReportRecipientViewSet, ReportScheduleViewSet,
    WeeklyReportViewSet,
)
from .views import (
    AlertsReportView, CheckinsReportView, FollowupsReportView,
    OverviewReportView, ReportTypesView, TravelersReportView,
)

# Router DRF pour les 4 ViewSets automatisés
router = DefaultRouter()
router.register("weekly", WeeklyReportViewSet, basename="weekly-report")
router.register("recipients", ReportRecipientViewSet, basename="report-recipient")
router.register("schedule", ReportScheduleViewSet, basename="report-schedule")
router.register("delivery-logs", ReportDeliveryLogViewSet, basename="report-delivery-log")


urlpatterns = [
    # ─── Legacy — exports à la volée ─────────────────────────────
    path("types/", ReportTypesView.as_view(), name="report-types"),
    path("travelers/", TravelersReportView.as_view(), name="report-travelers"),
    path("alerts/", AlertsReportView.as_view(), name="report-alerts"),
    path("followups/", FollowupsReportView.as_view(), name="report-followups"),
    path("checkins/", CheckinsReportView.as_view(), name="report-checkins"),
    path("overview/", OverviewReportView.as_view(), name="report-overview"),

    # ─── Automatisés — Phase 4 ─────────────────────────────────
    path("", include(router.urls)),
]
