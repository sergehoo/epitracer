from django import forms
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import CompanionLink, Traveler, TravelHistoryEntry
from .transport import entry_point_error


class TravelerAdminForm(forms.ModelForm):
    """Refuse un point d'entrée fermé ou incompatible avec le moyen de transport.
    Contrôlé seulement si l'un des deux change (fiches anciennes toujours modifiables)."""

    class Meta:
        model = Traveler
        # Champs effectivement affichés : ceux des fieldsets de TravelerAdmin.
        fields = ["transport_mode", "entry_point"]

    def clean(self):
        cleaned = super().clean()
        entry_changed = "entry_point" in self.changed_data
        if entry_changed or "transport_mode" in self.changed_data:
            error = entry_point_error(
                cleaned.get("transport_mode"), cleaned.get("entry_point"),
                check_active=entry_changed,
            )
            if error:
                self.add_error("entry_point", error)
        return cleaned


class TravelHistoryInline(admin.TabularInline):
    model = TravelHistoryEntry
    extra = 0


class CompanionInline(admin.TabularInline):
    model = CompanionLink
    fk_name = "traveler"
    extra = 0


@admin.register(Traveler)
class TravelerAdmin(GISModelAdmin):
    form = TravelerAdminForm
    list_display = (
        "public_id", "last_name", "first_name", "nationality",
        "arrival_date", "entry_point", "current_health_status",
        "created_at",
    )
    list_filter = (
        "current_health_status", "transport_mode", "gender", "entry_point",
        "created_at",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    search_fields = ("public_id", "first_name", "last_name", "id_document_number", "phone_mobile", "email")
    inlines = [TravelHistoryInline, CompanionInline]
    fieldsets = (
        ("Section 1 — Voyage", {"fields": (
            "arrival_date", "arrival_time", "transport_mode",
            "flight_or_voyage_number", "seat_number", "entry_point",
        )}),
        ("Section 2 — Identité & contacts", {"fields": (
            "last_name", "first_name", "middle_name", "date_of_birth",
            "age", "age_unit", "gender", "profession",
            "id_document_type", "id_document_number", "id_document_country", "nationality",
            "phone_mobile", "email", "postal_address",
        )}),
        ("Section 4 — Confinement en Côte d'Ivoire", {"fields": (
            "confinement_city", "confinement_commune", "confinement_neighborhood",
            "confinement_street_number", "confinement_lot",
            "confinement_hotel", "confinement_room_number",
            "emergency_phone_ci", "confinement_location",
            "confinement_address",
        )}),
        ("Section 7 — Déclaration", {"fields": (
            "consented_data_processing", "signed_at", "signed_place", "consent_signature",
        )}),
        ("Statut", {"fields": ("current_health_status", "user")}),
    )
    readonly_fields = ("public_id", "confinement_address")
