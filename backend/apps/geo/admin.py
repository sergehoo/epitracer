from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Country, EntryPoint, HealthZone


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "region", "risk_level")
    list_filter = ("region", "risk_level")
    search_fields = ("code", "code3", "name")


@admin.register(EntryPoint)
class EntryPointAdmin(GISModelAdmin):
    list_display = ("name", "type", "country", "city", "iata_code", "is_active")
    list_filter = ("type", "country", "is_active")
    search_fields = ("code", "name", "iata_code")


@admin.register(HealthZone)
class HealthZoneAdmin(GISModelAdmin):
    list_display = ("name", "level", "risk_level", "parent", "population")
    list_filter = ("level", "risk_level")
    search_fields = ("code", "name")
