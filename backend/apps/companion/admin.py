from django.contrib import admin

from .models import DataAccessLog, PrivacyConsent, PushSubscription, TravelerLocationPing


@admin.register(PrivacyConsent)
class PrivacyConsentAdmin(admin.ModelAdmin):
    list_display = ("traveler", "scope", "granted", "consent_version", "granted_at", "revoked_at")
    list_filter = ("scope", "granted", "consent_version")
    search_fields = ("traveler__public_id", "traveler__last_name", "traveler__first_name")
    readonly_fields = ("granted_at", "revoked_at", "ip_address", "user_agent",
                       "consent_text_excerpt", "created_at", "updated_at")


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("traveler", "device_type", "is_active", "failure_count", "last_used_at")
    list_filter = ("is_active", "device_type")
    search_fields = ("traveler__public_id", "endpoint")
    readonly_fields = ("endpoint", "p256dh", "auth", "user_agent", "last_used_at",
                       "failure_count", "created_at", "updated_at")


@admin.register(TravelerLocationPing)
class TravelerLocationPingAdmin(admin.ModelAdmin):
    list_display = ("traveler", "event_type", "source", "captured_at", "accuracy_m")
    list_filter = ("event_type", "source")
    search_fields = ("traveler__public_id",)
    readonly_fields = [f.name for f in TravelerLocationPing._meta.fields]


@admin.register(DataAccessLog)
class DataAccessLogAdmin(admin.ModelAdmin):
    list_display = ("traveler", "accessed_by", "resource", "accessed_at", "accessed_by_role")
    list_filter = ("resource", "accessed_by_role")
    search_fields = ("traveler__public_id", "accessed_by__email", "reason")
    readonly_fields = [f.name for f in DataAccessLog._meta.fields]
