from rest_framework import serializers

from .models import (
    DynamicForm,
    FieldCondition,
    FieldOption,
    FormAnswer,
    FormField,
    FormSection,
    FormSubmission,
)


class FieldOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldOption
        fields = ["id", "value", "label", "order", "triggers_risk"]


class FieldConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldCondition
        fields = ["id", "depends_on", "operator", "expected_value", "action"]


class FormFieldSerializer(serializers.ModelSerializer):
    options = FieldOptionSerializer(many=True, read_only=True)
    conditions = FieldConditionSerializer(many=True, read_only=True)

    class Meta:
        model = FormField
        # `section` est nécessaire en write pour créer un champ via l'admin.
        fields = [
            "id", "section", "code", "label", "help_text", "type", "is_required", "order",
            "min_value", "max_value", "min_length", "max_length",
            "regex", "default_value", "placeholder", "risk_weight",
            "options", "conditions",
        ]


class FormSectionSerializer(serializers.ModelSerializer):
    # En lecture, on inclut les champs imbriqués (renommés `fields_list` pour
    # ne pas entrer en conflit avec l'attribut DRF `Meta.fields`).
    fields_list = FormFieldSerializer(source="fields", many=True, read_only=True)

    class Meta:
        model = FormSection
        # `form` exposé en write pour créer/déplacer une section.
        fields = ["id", "form", "code", "title", "description", "order", "fields_list"]


class DynamicFormSerializer(serializers.ModelSerializer):
    sections = FormSectionSerializer(many=True, read_only=True)
    disease_code = serializers.CharField(source="disease.code", read_only=True)
    submissions_count = serializers.SerializerMethodField()

    class Meta:
        model = DynamicForm
        fields = [
            "id", "uuid", "disease", "disease_code", "code", "title", "description",
            "version", "is_active", "is_default", "sections", "submissions_count",
        ]

    def get_submissions_count(self, obj):
        # Compte les FormSubmission liées à ce formulaire — pratique sur la
        # liste admin pour identifier les formulaires les plus utilisés.
        return getattr(obj, "submissions", None).count() if hasattr(obj, "submissions") else 0


class FormAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormAnswer
        fields = [
            "id", "field", "value_text", "value_number", "value_bool",
            "value_date", "value_datetime", "value_options",
        ]


class FormSubmissionSerializer(serializers.ModelSerializer):
    answers = FormAnswerSerializer(many=True, required=False)

    class Meta:
        model = FormSubmission
        fields = [
            "id", "uuid", "form", "traveler", "submitted_by", "submitted_at",
            "is_complete", "raw_payload", "indexed_data", "answers",
        ]
        read_only_fields = ["submitted_by"]

    def create(self, validated):
        answers = validated.pop("answers", [])
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated["submitted_by"] = request.user
        submission = FormSubmission.objects.create(**validated)
        for a in answers:
            FormAnswer.objects.create(submission=submission, **a)
        return submission
