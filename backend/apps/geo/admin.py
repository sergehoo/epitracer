from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html

from .models import Country, EntryPoint, HealthZone


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "region", "risk_level")
    list_filter = ("region", "risk_level")
    search_fields = ("code", "code3", "name")
    ordering = ("name",)


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
        "name", "level_badge", "parent_name", "risk_level", "population",
        "has_geometry", "code",
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
            "country": "#0B1820", "pres": "#FF7F00", "region": "#009E60",
            "district": "#0EA5E9", "commune": "#7C3AED", "quartier": "#94A3B8",
            "custom": "#64748B",
        }
        color = colors.get(obj.level, "#64748B")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_level_display(),
        )

    @admin.display(description="Géom.", boolean=True)
    def has_geometry(self, obj):
        return obj.geometry is not None
