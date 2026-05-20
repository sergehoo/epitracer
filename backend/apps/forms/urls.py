from rest_framework.routers import DefaultRouter

from .views import DynamicFormViewSet, FormSubmissionViewSet

router = DefaultRouter()
router.register("definitions", DynamicFormViewSet, basename="dynamic-form")
router.register("submissions", FormSubmissionViewSet, basename="form-submission")
urlpatterns = router.urls
