"""Admin Django pour les modèles `medical`.

Objectif limité : permettre la consultation/debug en cas d'incident.
L'UX riche se fait via les vues frontend (Phases 9C+).
"""
from __future__ import annotations

from django.contrib import admin

from .models import (
    CaseClassification,
    DiseaseFollowupProtocol,
    FollowUpAction,
    LabAnalysis,
    MedicalSample,
    MedicalSymptomReport,
)


@admin.register(DiseaseFollowupProtocol)
class DiseaseFollowupProtocolAdmin(admin.ModelAdmin):
    list_display = (
        "disease", "duration_days", "daily_checkin_required",
        "require_geolocation", "geolocation_alert_after_hours", "is_active",
    )
    list_filter = ("is_active", "daily_checkin_required", "require_geolocation")
    search_fields = ("disease__code", "disease__name")


@admin.register(MedicalSymptomReport)
class MedicalSymptomReportAdmin(admin.ModelAdmin):
    list_display = (
        "symptom_code", "severity", "onset_date", "source",
        "reported_by_traveler", "is_critical", "followup_case",
    )
    list_filter = ("severity", "source", "is_critical", "reported_by_traveler")
    search_fields = (
        "symptom_code", "symptom_label",
        "followup_case__traveler__public_id",
    )
    date_hierarchy = "onset_date"


@admin.register(MedicalSample)
class MedicalSampleAdmin(admin.ModelAdmin):
    list_display = (
        "sample_code", "sample_type", "transport_status",
        "collected_at", "received_at", "destination_lab", "followup_case",
    )
    list_filter = ("sample_type", "transport_status")
    search_fields = (
        "sample_code", "destination_lab",
        "followup_case__traveler__public_id",
    )
    date_hierarchy = "created_at"


@admin.register(LabAnalysis)
class LabAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "test_type", "lab_name", "status", "result",
        "received_at", "validated_at", "sample",
    )
    list_filter = ("status", "result", "lab_name")
    search_fields = (
        "test_type", "lab_name",
        "sample__sample_code",
        "sample__followup_case__traveler__public_id",
    )
    date_hierarchy = "created_at"


@admin.register(CaseClassification)
class CaseClassificationAdmin(admin.ModelAdmin):
    list_display = (
        "followup_case", "classification", "is_current",
        "classified_by", "classified_at",
    )
    list_filter = ("classification", "is_current")
    search_fields = (
        "followup_case__traveler__public_id",
        "classified_by__email",
    )
    date_hierarchy = "classified_at"


@admin.register(FollowUpAction)
class FollowUpActionAdmin(admin.ModelAdmin):
    list_display = (
        "action_type", "title", "status",
        "performed_by", "performed_at", "followup_case",
    )
    list_filter = ("action_type", "status")
    search_fields = (
        "title", "description",
        "followup_case__traveler__public_id",
    )
    date_hierarchy = "performed_at"
