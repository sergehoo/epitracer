from django.contrib import admin

from .models import Disease, RiskFactor, Symptom


class SymptomInline(admin.TabularInline):
    model = Symptom
    extra = 0


class RiskFactorInline(admin.TabularInline):
    model = RiskFactor
    extra = 0


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "severity", "is_active", "requires_quarantine", "surveillance_days")
    list_filter = ("severity", "is_active", "requires_quarantine", "requires_pass")
    search_fields = ("name", "code", "short_name")
    inlines = [SymptomInline, RiskFactorInline]
