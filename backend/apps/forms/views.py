from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import DynamicForm, FormSubmission
from .serializers import DynamicFormSerializer, FormSubmissionSerializer


class DynamicFormViewSet(viewsets.ModelViewSet):
    queryset = (
        DynamicForm.objects.select_related("disease")
        .prefetch_related("sections__fields__options", "sections__fields__conditions")
        .all()
    )
    serializer_class = DynamicFormSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["disease", "is_active", "is_default"]
    search_fields = ["code", "title", "disease__code"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()


class FormSubmissionViewSet(viewsets.ModelViewSet):
    queryset = FormSubmission.objects.select_related("form", "traveler", "submitted_by").all()
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticatedAndActive]
    filterset_fields = ["form", "traveler", "is_complete"]
