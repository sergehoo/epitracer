from rest_framework.routers import DefaultRouter

from .views import (
    DynamicFormViewSet, FieldOptionViewSet, FormFieldViewSet,
    FormSectionViewSet, FormSubmissionViewSet,
)

router = DefaultRouter()
router.register("definitions", DynamicFormViewSet, basename="dynamic-form")
router.register("sections", FormSectionViewSet, basename="form-section")
router.register("fields", FormFieldViewSet, basename="form-field")
router.register("options", FieldOptionViewSet, basename="form-option")
router.register("submissions", FormSubmissionViewSet, basename="form-submission")

urlpatterns = router.urls
