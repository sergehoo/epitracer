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

urlpatterns = router.urls + [
    path("verify/", QRVerifyView.as_view(), name="pass-verify"),
    path("public-key.pem", PublicKeyView.as_view(), name="pass-public-key"),
]
