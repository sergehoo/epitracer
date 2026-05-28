"""URLs du module notifications.

Endpoints exposés (préfixés par /api/v1/notifications/) :

    GET  /templates/                       — liste des templates
    POST /templates/                       — créer un template (admin)
    GET  /                                 — liste / historique notifications
    GET  /<id>/                            — détail
    POST /send/                            — envoi manuel
    POST /preview-routing/                 — pré-validation provider
    POST /<id>/retry/                      — relance une notif FAILED
    POST /<id>/cancel/                     — annule une notif PENDING/QUEUED
    GET  /traveler/<public_id>/            — historique d'un voyageur
    POST /webhooks/twilio/sms/status/      — delivery report Twilio
    POST /webhooks/orange-ci/sms/status/   — delivery report Orange CI
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    MetaWhatsAppWebhookView, NotificationTemplateViewSet,
    NotificationViewSet, OrangeCiSmsStatusWebhookView,
    TravelerNotificationsView, TwilioSmsStatusWebhookView,
    TwilioWhatsAppStatusWebhookView,
)

router = DefaultRouter()
router.register("templates", NotificationTemplateViewSet, basename="notification-template")

urlpatterns = [
    # Webhooks AVANT le router (sinon le router intercepte)
    path(
        "webhooks/twilio/sms/status/",
        TwilioSmsStatusWebhookView.as_view(),
        name="twilio-sms-webhook",
    ),
    path(
        "webhooks/orange-ci/sms/status/",
        OrangeCiSmsStatusWebhookView.as_view(),
        name="orange-ci-sms-webhook",
    ),
    # WhatsApp delivery reports
    path(
        "webhooks/twilio/whatsapp/status/",
        TwilioWhatsAppStatusWebhookView.as_view(),
        name="twilio-whatsapp-webhook",
    ),
    path(
        "webhooks/meta/whatsapp/",
        MetaWhatsAppWebhookView.as_view(),
        name="meta-whatsapp-webhook",
    ),
    # Historique par voyageur
    path(
        "traveler/<str:public_id>/",
        TravelerNotificationsView.as_view(),
        name="traveler-notifications",
    ),
]

# Important : enregistrer NotificationViewSet en LAST avec préfixe vide
# pour qu'il accepte /api/v1/notifications/ et /api/v1/notifications/<id>/.
router.register("", NotificationViewSet, basename="notification")
urlpatterns += router.urls
