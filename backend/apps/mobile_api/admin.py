from django.contrib import admin

from .models import AssistanceRequest, LocationShare, MobileDevice, Vaccination


@admin.register(MobileDevice)
class MobileDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "app_version", "is_active", "last_seen_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__email", "fcm_token", "device_id")
    readonly_fields = ("last_seen_at", "created_at", "updated_at")


@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    list_display = (
        "disease_name", "vaccine_name", "user", "administered_at",
        "dose_number", "verified",
    )
    list_filter = ("disease_code", "verified", "country_code")
    search_fields = ("user__email", "vaccine_name", "lot_number", "center_name")
    date_hierarchy = "administered_at"


@admin.register(AssistanceRequest)
class AssistanceRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "callback_phone", "status", "assigned_to")
    list_filter = ("status",)
    search_fields = ("user__email", "callback_phone", "reason", "message")
    autocomplete_fields = ("assigned_to",)
    date_hierarchy = "created_at"


@admin.register(LocationShare)
class LocationShareAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "latitude", "longitude", "context")
    list_filter = ("context",)
    search_fields = ("user__email",)
    date_hierarchy = "created_at"
