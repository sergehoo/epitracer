from django.urls import path
from rest_framework.routers import DefaultRouter

from .relations import TravelerRelationsView
from .views import HealthAlertViewSet

router = DefaultRouter()
router.register("alerts", HealthAlertViewSet, basename="alert")
urlpatterns = router.urls + [
    path("relations/", TravelerRelationsView.as_view(), name="traveler-relations"),
]
