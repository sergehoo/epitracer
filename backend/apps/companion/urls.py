"""
URLs publiques du module Companion.

Toutes les routes sont mountées sous /api/v1/public/ (voir
config/urls.py). Le préfixe `public/` signale clairement qu'il s'agit
d'endpoints non authentifiés (lookup par public_id voyageur).
"""
from django.urls import path

from .views import (
    CheckinView,
    ConsentView,
    FollowUpStatusView,
    LocationPingView,
    MyDataExportView,
    MyDataSummaryView,
    PushPublicKeyView,
    PushSubscribeView,
    PushUnsubscribeView,
)

urlpatterns = [
    path("consent/", ConsentView.as_view(), name="companion-consent"),
    path("checkin/", CheckinView.as_view(), name="companion-checkin"),
    path("location/ping/", LocationPingView.as_view(), name="companion-location-ping"),
    path("follow-up/status/", FollowUpStatusView.as_view(), name="companion-followup-status"),
    path("push/public-key/", PushPublicKeyView.as_view(), name="companion-push-public-key"),
    path("push/subscribe/", PushSubscribeView.as_view(), name="companion-push-subscribe"),
    path("push/unsubscribe/", PushUnsubscribeView.as_view(), name="companion-push-unsubscribe"),
    # RGPD self-service voyageur
    path("me/data-summary/", MyDataSummaryView.as_view(), name="companion-me-data-summary"),
    path("me/export/", MyDataExportView.as_view(), name="companion-me-export"),
]
