"""Admin Django pour les rapports automatisés.

Réservé Super Admin (RBAC dur au niveau du groupe Django).
"""
from django.contrib import admin

from .models import (
    AutomatedReportRecipient, AutomatedReportSchedule,
    GeneratedReport, ReportDeliveryLog,
)


@admin.register(AutomatedReportSchedule)
class AutomatedReportScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "report_type", "weekday", "time", "timezone", "is_active")
    list_filter = ("report_type", "is_active", "timezone")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at", "created_by")


@admin.register(AutomatedReportRecipient)
class AutomatedReportRecipientAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "organization", "preferred_channel", "masked_phone",
        "email", "is_active", "consent_date",
    )
    list_filter = ("preferred_channel", "is_active", "language", "district")
    search_fields = ("full_name", "email", "organization")
    readonly_fields = ("created_at", "updated_at", "created_by", "masked_phone")
    fieldsets = (
        (None, {"fields": (
            "full_name", "job_title", "organization",
            "phone_number", "masked_phone", "email",
            "preferred_channel", "language", "district",
            "allowed_report_types", "is_active",
        )}),
        ("Consentement (obligatoire)", {"fields": (
            "consent_date", "consent_evidence",
        )}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_at")}),
    )


@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = (
        "report_code", "report_type", "period_start", "period_end",
        "status", "generated_at",
    )
    list_filter = ("report_type", "status")
    search_fields = ("report_code",)
    readonly_fields = (
        "report_code", "created_at", "updated_at", "generated_by",
        "duration_ms", "summary_data",
    )
    ordering = ("-period_start",)


@admin.register(ReportDeliveryLog)
class ReportDeliveryLogAdmin(admin.ModelAdmin):
    list_display = (
        "report", "recipient", "channel", "provider",
        "destination_masked", "status", "retry_count", "sent_at",
    )
    list_filter = ("channel", "status", "provider")
    search_fields = ("destination_masked", "report__report_code", "recipient__full_name")
    readonly_fields = (
        "created_at", "updated_at", "report", "recipient", "channel",
        "provider", "destination_masked", "notification_id",
        "sent_at", "delivered_at", "retry_count",
    )
