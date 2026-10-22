from django.contrib import admin, messages

from .models import Disease, RiskFactor, Symptom


class SymptomInline(admin.TabularInline):
    model = Symptom
    extra = 0


class RiskFactorInline(admin.TabularInline):
    model = RiskFactor
    extra = 0


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "severity", "is_active", "is_published", "public_alert_level",
        "surveillance_days",
    )
    list_filter = (
        "severity", "is_active", "is_published", "public_alert_level", "requires_quarantine",
    )
    search_fields = ("name", "code", "short_name")
    inlines = [SymptomInline, RiskFactorInline]
    readonly_fields = ("is_published", "published_at", "published_by")
    actions = ["publish_selected", "unpublish_selected"]
    fieldsets = (
        (None, {"fields": (
            "name", "code", "short_name", "icd11_code", "severity", "color", "is_active",
            "requires_quarantine", "requires_pass",
        )}),
        ("Épidémiologie", {"fields": (
            "incubation_min_days", "incubation_max_days", "surveillance_days", "quarantine_days",
            "transmission_modes", "risk_countries", "case_definition", "protocols",
            "notification_rules",
        )}),
        ("Portail public", {"fields": (
            "slug", "description", "transmission_details", "prevention",
            "traveler_recommendations", "public_alert_level", "public_translations",
            "is_published", "published_at", "published_by",
        )}),
    )

    @admin.action(description="Publier sur le portail")
    def publish_selected(self, request, queryset):
        self._apply(request, queryset, "publish_disease")

    @admin.action(description="Retirer du portail")
    def unpublish_selected(self, request, queryset):
        self._apply(request, queryset, "unpublish_disease")

    def _apply(self, request, queryset, service_name):
        from django.core.exceptions import PermissionDenied, ValidationError

        from apps.portal import services

        done = 0
        for disease in queryset:
            try:
                getattr(services, service_name)(disease, request.user)
                done += 1
            except (PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"{disease.name} : {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"{done} fiche(s) mise(s) à jour.", level=messages.SUCCESS)
