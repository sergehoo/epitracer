"""URLs du centre de rapports."""
from django.urls import path

from .views import (
    AlertsReportView,
    CheckinsReportView,
    FollowupsReportView,
    OverviewReportView,
    ReportTypesView,
    TravelersReportView,
)

urlpatterns = [
    path("types/", ReportTypesView.as_view(), name="report-types"),
    path("travelers/", TravelersReportView.as_view(), name="report-travelers"),
    path("alerts/", AlertsReportView.as_view(), name="report-alerts"),
    path("followups/", FollowupsReportView.as_view(), name="report-followups"),
    path("checkins/", CheckinsReportView.as_view(), name="report-checkins"),
    path("overview/", OverviewReportView.as_view(), name="report-overview"),
]
