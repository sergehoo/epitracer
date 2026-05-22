"""URLs admin du module Companion."""
from django.urls import path

from .admin_views import (
    ActiveFollowupsMapView,
    FollowupsOverviewView,
    TravelerAccessLogView,
    TravelerLocationsView,
)

urlpatterns = [
    path("followups/", FollowupsOverviewView.as_view(), name="companion-admin-followups"),
    path("map/active-followups/", ActiveFollowupsMapView.as_view(), name="companion-admin-map"),
    path("travelers/<str:public_id>/locations/",
         TravelerLocationsView.as_view(), name="companion-admin-traveler-locations"),
    path("travelers/<str:public_id>/access-log/",
         TravelerAccessLogView.as_view(), name="companion-admin-traveler-access-log"),
]
