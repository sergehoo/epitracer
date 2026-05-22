from django.urls import path

from .views import (
    DashboardOverviewView,
    EntryPointFlowsView,
    HeatmapView,
    NationalDashboardView,
    TrackVisitView,
    VisitsOverviewView,
)

urlpatterns = [
    path("overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("national/", NationalDashboardView.as_view(), name="dashboard-national"),
    path("entry-point-flows/", EntryPointFlowsView.as_view(), name="entry-point-flows"),
    path("heatmap/", HeatmapView.as_view(), name="heatmap"),

    # Visites
    path("visits/track/", TrackVisitView.as_view(), name="visit-track"),
    path("visits/overview/", VisitsOverviewView.as_view(), name="visit-overview"),
]
