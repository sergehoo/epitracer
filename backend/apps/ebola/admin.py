from django.contrib import admin

from .models import EbolaDeclaration, EbolaExposureAssessment, EbolaInvestigation, EbolaSymptomReport


class EbolaExposureInline(admin.StackedInline):
    model = EbolaExposureAssessment
    extra = 0
    can_delete = False


class EbolaDeclarationInline(admin.StackedInline):
    model = EbolaDeclaration
    extra = 0
    can_delete = False


class EbolaSymptomReportInline(admin.TabularInline):
    model = EbolaSymptomReport
    extra = 0


@admin.register(EbolaInvestigation)
class EbolaInvestigationAdmin(admin.ModelAdmin):
    list_display = (
        "case_number", "traveler", "status", "risk_level", "risk_score",
        "entry_point", "surveillance_start", "surveillance_end",
    )
    list_filter = ("status", "risk_level", "entry_point")
    search_fields = ("case_number", "traveler__public_id", "traveler__last_name")
    inlines = [EbolaExposureInline, EbolaSymptomReportInline, EbolaDeclarationInline]
