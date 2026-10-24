from django import forms
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import Country, CountryRiskAssessment, EntryPoint, HealthZone
from .services import refresh_country_risk, save_new_assessment, validate_assessment


class CountryRiskAssessmentForm(forms.ModelForm):
    class Meta:
        model = CountryRiskAssessment
        fields = [
            "country",
            "disease",
            "risk_level",
            "valid_from",
            "valid_until",
            "justification",
            "source_alert",
            "source_reference",
        ]

    def clean(self):
        data = super().clean()
        if self.instance.pk is None and data.get("risk_level"):
            try:
                validate_assessment(
                    risk_level=data["risk_level"],
                    justification=data.get("justification", ""),
                    valid_from=data.get("valid_from"),
                    valid_until=data.get("valid_until"),
                    source_alert=data.get("source_alert"),
                    source_reference=data.get("source_reference", ""),
                )
            except ValidationError as exc:
                raise ValidationError(exc.message_dict) from exc
        elif self.instance.pk is not None:
            until = data.get("valid_until")
            if until and until < self.instance.valid_from:
                raise ValidationError(
                    {"valid_until": "La fin de validité précède la date d'effet."}
                )
        return data


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "code3", "name", "region", "is_monitored", "risk_level")
    list_filter = ("region", "is_monitored", "risk_level")
    search_fields = ("code", "code3", "name")
    ordering = ("name",)
    # Calculés à partir des évaluations : à modifier via « Évaluations du risque pays ».
    readonly_fields = ("risk_level", "risk_for_diseases")


@admin.register(CountryRiskAssessment)
class CountryRiskAssessmentAdmin(SimpleHistoryAdmin):
    form = CountryRiskAssessmentForm
    list_display = (
        "country",
        "disease",
        "risk_level",
        "valid_from",
        "valid_until",
        "superseded_by",
        "decided_by",
    )
    list_filter = ("risk_level", "disease", "country__is_monitored")
    search_fields = (
        "country__code",
        "country__code3",
        "country__name",
        "justification",
        "source_reference",
    )
    autocomplete_fields = ("country",)
    raw_id_fields = ("source_alert",)
    readonly_fields = ("decided_by", "superseded_by")
    date_hierarchy = "valid_from"

    def get_readonly_fields(self, request, obj=None):
        # Une évaluation enregistrée ne se réécrit pas : seule sa fin de validité évolue.
        if obj is not None:
            return [f.name for f in self.model._meta.fields if f.name != "valid_until"]
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "Fin de validité modifiée depuis l'admin"
            super().save_model(request, obj, form, change)
            refresh_country_risk(obj.country)
            return
        obj.decided_by = request.user
        save_new_assessment(obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EntryPoint)
class EntryPointAdmin(GISModelAdmin):
    list_display = ("name", "type", "country", "city", "iata_code", "is_active")
    list_filter = ("type", "country", "is_active")
    search_fields = ("code", "name", "iata_code")
    autocomplete_fields = ("country",)
    ordering = ("name",)


@admin.register(HealthZone)
class HealthZoneAdmin(GISModelAdmin):
    list_display = (
        "name",
        "level_badge",
        "parent_name",
        "risk_level",
        "population",
        "has_geometry",
        "code",
    )
    list_filter = ("level", "risk_level")
    list_select_related = ("parent",)
    search_fields = ("code", "name", "parent__name")
    # `parent` peut référencer une autre HealthZone parmi des centaines
    # → autocomplete pour éviter un <select> de 370+ entrées.
    autocomplete_fields = ("parent",)
    ordering = ("level", "name")
    list_per_page = 50

    # Affiche le nom du parent au lieu de "HealthZone object (129)"
    @admin.display(description="Parent", ordering="parent__name")
    def parent_name(self, obj):
        return str(obj.parent) if obj.parent_id else "—"

    @admin.display(description="Niveau")
    def level_badge(self, obj):
        colors = {
            "country": "#0B1820",
            "pres": "#FF7F00",
            "region": "#009E60",
            "district": "#0EA5E9",
            "commune": "#7C3AED",
            "quartier": "#94A3B8",
            "custom": "#64748B",
        }
        color = colors.get(obj.level, "#64748B")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color,
            obj.get_level_display(),
        )

    @admin.display(description="Géom.", boolean=True)
    def has_geometry(self, obj):
        return obj.geometry is not None
