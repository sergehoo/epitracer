from rest_framework.routers import DefaultRouter

from .views import (
    CountryRiskAssessmentViewSet,
    CountryViewSet,
    EntryPointViewSet,
    HealthZoneViewSet,
)

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="country")
router.register("country-risks", CountryRiskAssessmentViewSet, basename="country-risk")
router.register("entry-points", EntryPointViewSet, basename="entry-point")
router.register("zones", HealthZoneViewSet, basename="health-zone")
urlpatterns = router.urls
