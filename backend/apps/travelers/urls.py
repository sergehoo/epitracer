from rest_framework.routers import DefaultRouter

from .views import CompanionLinkViewSet, TravelerViewSet, TravelHistoryViewSet

router = DefaultRouter()
router.register("", TravelerViewSet, basename="traveler")
router.register("travel-history", TravelHistoryViewSet, basename="travel-history")
router.register("companions", CompanionLinkViewSet, basename="companion")
urlpatterns = router.urls
