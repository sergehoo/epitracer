from django.contrib import admin

from .models import HealthPass, PassBlacklistEntry, PassVerificationLog


@admin.register(HealthPass)
class HealthPassAdmin(admin.ModelAdmin):
    list_display = ("pass_number", "traveler", "disease", "status", "risk_level", "issued_at", "expires_at")
    list_filter = ("status", "risk_level", "disease")
    search_fields = ("pass_number", "traveler__public_id", "traveler__last_name")
    readonly_fields = ("payload", "signature_b64", "signing_kid", "qr_image", "pdf_file")


@admin.register(PassBlacklistEntry)
class PassBlacklistEntryAdmin(admin.ModelAdmin):
    list_display = ("pass_number", "reason", "added_by", "created_at")
    search_fields = ("pass_number", "reason")


@admin.register(PassVerificationLog)
class PassVerificationLogAdmin(admin.ModelAdmin):
    list_display = ("verified_at", "pass_number", "is_valid", "reason", "entry_point", "verified_by")
    list_filter = ("is_valid", "entry_point")
    search_fields = ("pass_number", "reason")
    date_hierarchy = "verified_at"
