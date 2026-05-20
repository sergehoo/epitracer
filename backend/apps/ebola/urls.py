from django.urls import path
from rest_framework.routers import DefaultRouter

from .public_views import PublicPassConsultView, PublicTravelerRegisterView
from .views import EbolaInvestigationViewSet

router = DefaultRouter()
router.register("investigations", EbolaInvestigationViewSet, basename="ebola-investigation")

urlpatterns = router.urls + [
    # Endpoints PUBLICS (portail voyageurs)
    path("public/register/", PublicTravelerRegisterView.as_view(), name="ebola-public-register"),
    path("public/pass/<str:public_id>/", PublicPassConsultView.as_view(), name="ebola-public-pass"),
]
