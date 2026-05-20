from rest_framework.routers import DefaultRouter

from .views import HealthAlertViewSet

router = DefaultRouter()
router.register("alerts", HealthAlertViewSet, basename="alert")
urlpatterns = router.urls
