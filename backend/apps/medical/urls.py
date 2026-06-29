"""URLs du module medical (Phase 9B).

Deux espaces d'URL :
  - admin_urlpatterns : monté sous /api/v1/admin/followups/ (auth requise)
  - public_urlpatterns : monté sous /api/v1/public/followup/ (AllowAny + throttle)

Les endpoints publics check-in / location réutilisent les vues
existantes d'apps.companion pour éviter toute duplication.
"""
from __future__ import annotations

from django.urls import path

from apps.companion.views import CheckinView, LocationPingView

from .views import (
    FollowupActionsView,
    FollowupAssignAgentView,
    FollowupAuditView,
    FollowupClassifyView,
    FollowupCloseView,
    FollowupDetailView,
    FollowupDocumentsView,
    FollowupLabResultsView,
    FollowupLabValidateView,
    FollowupListView,
    FollowupLocationHistoryView,
    FollowupNotifyView,
    FollowupSampleUpdateView,
    FollowupSamplesView,
    FollowupSymptomsView,
    FollowupTimelineView,
    PublicAssistanceView,
    PublicFollowupStatusView,
    PublicSymptomReportView,
)

admin_urlpatterns = [
    path("", FollowupListView.as_view(), name="medical-followup-list"),
    path("<str:traveler_id>/", FollowupDetailView.as_view(), name="medical-followup-detail"),
    path("<str:traveler_id>/timeline/", FollowupTimelineView.as_view(), name="medical-followup-timeline"),
    path("<str:traveler_id>/actions/", FollowupActionsView.as_view(), name="medical-followup-actions"),
    path("<str:traveler_id>/symptoms/", FollowupSymptomsView.as_view(), name="medical-followup-symptoms"),
    path("<str:traveler_id>/samples/", FollowupSamplesView.as_view(), name="medical-followup-samples"),
    path(
        "<str:traveler_id>/samples/<int:sample_id>/",
        FollowupSampleUpdateView.as_view(),
        name="medical-followup-sample-update",
    ),
    path(
        "<str:traveler_id>/lab-results/",
        FollowupLabResultsView.as_view(),
        name="medical-followup-lab-results",
    ),
    path(
        "<str:traveler_id>/lab-results/<int:analysis_id>/validate/",
        FollowupLabValidateView.as_view(),
        name="medical-followup-lab-validate",
    ),
    path("<str:traveler_id>/classify/", FollowupClassifyView.as_view(), name="medical-followup-classify"),
    path("<str:traveler_id>/notify/", FollowupNotifyView.as_view(), name="medical-followup-notify"),
    path(
        "<str:traveler_id>/assign-agent/",
        FollowupAssignAgentView.as_view(),
        name="medical-followup-assign-agent",
    ),
    path("<str:traveler_id>/close/", FollowupCloseView.as_view(), name="medical-followup-close"),
    path("<str:traveler_id>/documents/", FollowupDocumentsView.as_view(), name="medical-followup-documents"),
    path("<str:traveler_id>/audit/", FollowupAuditView.as_view(), name="medical-followup-audit"),
    path(
        "<str:traveler_id>/location-history/",
        FollowupLocationHistoryView.as_view(),
        name="medical-followup-location-history",
    ),
]

public_urlpatterns = [
    path("status/", PublicFollowupStatusView.as_view(), name="medical-public-status"),
    path("checkin/", CheckinView.as_view(), name="medical-public-checkin"),
    path("symptoms/", PublicSymptomReportView.as_view(), name="medical-public-symptoms"),
    path("location/", LocationPingView.as_view(), name="medical-public-location"),
    path("assistance/", PublicAssistanceView.as_view(), name="medical-public-assistance"),
]
