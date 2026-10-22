from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PublicDiseaseDetailView,
    PublicDiseaseListView,
    PublicNoticeAdminViewSet,
    PublicNoticeListView,
    RegistrationConfigView,
)

# Gestion (authentifiée) : /api/v1/portal/
router = DefaultRouter()
router.register("notices", PublicNoticeAdminViewSet, basename="portal-notice")
urlpatterns = router.urls

# Lecture publique (sans authentification) : /api/v1/public/
public_urlpatterns = [
    path("diseases/", PublicDiseaseListView.as_view(), name="public-diseases"),
    path("diseases/<slug:slug>/", PublicDiseaseDetailView.as_view(), name="public-disease-detail"),
    path("notices/", PublicNoticeListView.as_view(), name="public-notices"),
    path(
        "registration-config/", RegistrationConfigView.as_view(), name="public-registration-config"
    ),
]
