from rest_framework.routers import DefaultRouter

from .views import CountryViewSet, EntryPointViewSet, HealthZoneViewSet

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="country")
router.register("entry-points", EntryPointViewSet, basename="entry-point")
router.register("zones", HealthZoneViewSet, basename="health-zone")
urlpatterns = router.urls
