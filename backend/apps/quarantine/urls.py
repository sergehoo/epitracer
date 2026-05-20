from rest_framework.routers import DefaultRouter

from .views import DailyCheckViewSet, FollowUpVisitViewSet, QuarantineRecordViewSet

router = DefaultRouter()
router.register("", QuarantineRecordViewSet, basename="quarantine")
router.register("daily-checks", DailyCheckViewSet, basename="daily-check")
router.register("visits", FollowUpVisitViewSet, basename="visit")
urlpatterns = router.urls
