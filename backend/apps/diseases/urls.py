from rest_framework.routers import DefaultRouter

from .views import DiseaseViewSet, RiskFactorViewSet, SymptomViewSet

router = DefaultRouter()
router.register("", DiseaseViewSet, basename="disease")
router.register("symptoms", SymptomViewSet, basename="symptom")
router.register("risk-factors", RiskFactorViewSet, basename="risk-factor")
urlpatterns = router.urls
