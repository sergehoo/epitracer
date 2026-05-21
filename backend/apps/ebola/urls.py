from django.urls import path
from rest_framework.routers import DefaultRouter

from .public_views import (
    PublicOfficialFormPdfView,
    PublicPassConsultView,
    PublicPassPdfView,
    PublicPassportUploadView,
    PublicTravelerRegisterView,
)
from .views import EbolaInvestigationViewSet

router = DefaultRouter()
router.register("investigations", EbolaInvestigationViewSet, basename="ebola-investigation")

urlpatterns = router.urls + [
    # Endpoints PUBLICS (portail voyageurs)
    path("public/register/", PublicTravelerRegisterView.as_view(),
         name="ebola-public-register"),
    path("public/pass/<str:public_id>/", PublicPassConsultView.as_view(),
         name="ebola-public-pass"),
    path("public/pass/<str:public_id>/pdf/", PublicPassPdfView.as_view(),
         name="ebola-public-pass-pdf"),
    path("public/pass/<str:public_id>/official-form.pdf",
         PublicOfficialFormPdfView.as_view(),
         name="ebola-public-official-form"),
    path("public/upload-passport/<str:public_id>/",
         PublicPassportUploadView.as_view(),
         name="ebola-public-upload-passport"),
]
