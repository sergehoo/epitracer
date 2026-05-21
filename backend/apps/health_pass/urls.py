from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    HealthPassViewSet,
    PassBlacklistViewSet,
    PassVerificationLogViewSet,
    PublicKeyView,
    QRVerifyView,
)

router = DefaultRouter()
router.register("", HealthPassViewSet, basename="health-pass")
router.register("blacklist", PassBlacklistViewSet, basename="pass-blacklist")
router.register("verifications", PassVerificationLogViewSet, basename="pass-verification")

# IMPORTANT : `public-key.pem` et `verify/` doivent être déclarés AVANT
# `router.urls`. DRF active le "format suffix" par défaut, donc une URL comme
# `/passes/public-key.pem` est interprétée par le router comme
# `<pk>=public-key` + `format=pem` (et tape la vue de détail au lieu de la vue
# publique de clé). Placer ces paths en tête garantit qu'ils sont matchés en
# premier.
urlpatterns = [
    path("public-key.pem", PublicKeyView.as_view(), name="pass-public-key"),
    path("verify/", QRVerifyView.as_view(), name="pass-verify"),
] + router.urls
