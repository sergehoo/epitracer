from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import (
    DynamicForm, FieldOption, FormField, FormSection, FormSubmission,
)
from .serializers import (
    DynamicFormSerializer, FieldOptionSerializer, FormFieldSerializer,
    FormSectionSerializer, FormSubmissionSerializer,
)


# ---------------------------------------------------------------------------
# Permissions helper
# ---------------------------------------------------------------------------
EDITOR_ROLES = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]


class _EditorMixin:
    """Lecture pour tout authentifié, écriture réservée aux rôles éditeurs."""

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = EDITOR_ROLES
            return [IsAuthenticatedAndActive(), HasRole()]
        return [IsAuthenticated()]


# ---------------------------------------------------------------------------
# DynamicForm
# ---------------------------------------------------------------------------
class DynamicFormViewSet(_EditorMixin, viewsets.ModelViewSet):
    queryset = (
        DynamicForm.objects.select_related("disease")
        .prefetch_related("sections__fields__options", "sections__fields__conditions")
        .all()
    )
    serializer_class = DynamicFormSerializer
    filterset_fields = ["disease", "is_active", "is_default"]
    search_fields = ["code", "title", "disease__code"]


# ---------------------------------------------------------------------------
# FormSection
# ---------------------------------------------------------------------------
class FormSectionViewSet(_EditorMixin, viewsets.ModelViewSet):
    queryset = FormSection.objects.select_related("form").prefetch_related("fields__options").all()
    serializer_class = FormSectionSerializer
    filterset_fields = ["form"]
    search_fields = ["code", "title"]


# ---------------------------------------------------------------------------
# FormField
# ---------------------------------------------------------------------------
class FormFieldViewSet(_EditorMixin, viewsets.ModelViewSet):
    queryset = FormField.objects.select_related("section").prefetch_related("options", "conditions").all()
    serializer_class = FormFieldSerializer
    filterset_fields = ["section", "type", "is_required"]
    search_fields = ["code", "label"]


# ---------------------------------------------------------------------------
# FieldOption
# ---------------------------------------------------------------------------
class FieldOptionViewSet(_EditorMixin, viewsets.ModelViewSet):
    queryset = FieldOption.objects.select_related("field").all()
    serializer_class = FieldOptionSerializer
    filterset_fields = ["field"]


# ---------------------------------------------------------------------------
# FormSubmission (lecture uniquement pour l'admin — l'écriture passe par
# les endpoints publics pour les voyageurs)
# ---------------------------------------------------------------------------
class FormSubmissionViewSet(viewsets.ModelViewSet):
    queryset = FormSubmission.objects.select_related("form", "traveler", "submitted_by").all()
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticatedAndActive]
    filterset_fields = ["form", "traveler", "is_complete"]
