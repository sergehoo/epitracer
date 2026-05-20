from django.contrib import admin

from .models import (
    DynamicForm,
    FieldCondition,
    FieldOption,
    FormAnswer,
    FormField,
    FormSection,
    FormSubmission,
)


class FieldOptionInline(admin.TabularInline):
    model = FieldOption
    extra = 0


class FieldConditionInline(admin.TabularInline):
    model = FieldCondition
    extra = 0
    fk_name = "field"


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "type", "section", "is_required", "order", "risk_weight")
    list_filter = ("type", "is_required", "section__form")
    inlines = [FieldOptionInline, FieldConditionInline]


class FormFieldInline(admin.TabularInline):
    model = FormField
    extra = 0
    show_change_link = True
    fields = ("order", "code", "label", "type", "is_required", "risk_weight")


@admin.register(FormSection)
class FormSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "form", "order")
    inlines = [FormFieldInline]


class FormSectionInline(admin.TabularInline):
    model = FormSection
    extra = 0
    show_change_link = True


@admin.register(DynamicForm)
class DynamicFormAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "disease", "version", "is_active", "is_default")
    list_filter = ("disease", "is_active", "is_default")
    inlines = [FormSectionInline]


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ("uuid", "form", "traveler", "submitted_by", "submitted_at", "is_complete")
    list_filter = ("form", "is_complete")


admin.site.register(FormAnswer)
