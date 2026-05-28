from django.contrib import admin

from .models import (
    Notification, NotificationAuditLog, NotificationProviderConfig,
    NotificationTemplate,
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "disease", "channels_str")
    list_filter = ("is_active", "disease")
    search_fields = ("code", "name", "description")
    autocomplete_fields = ("disease",)

    @admin.display(description="Canaux")
    def channels_str(self, obj):
        return ", ".join(obj.channels or [])


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "channel", "provider", "masked_recipient",
        "status", "message_type", "retry_count", "sent_by",
    )
    list_filter = (
        "channel", "status", "provider", "direction", "message_type",
    )
    list_select_related = ("traveler", "template", "sent_by")
    search_fields = ("recipient", "normalized_phone", "provider_message_id", "body")
    autocomplete_fields = ("traveler", "template", "sent_by")
    date_hierarchy = "created_at"
    readonly_fields = (
        "uuid", "normalized_phone", "provider_message_id", "retry_count",
        "queued_at", "sent_at", "delivered_at", "failed_at", "metadata",
    )


@admin.register(NotificationProviderConfig)
class NotificationProviderConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "channel", "is_enabled", "priority", "country_code", "sender_name")
    list_filter = ("provider", "channel", "is_enabled", "country_code")
    list_editable = ("is_enabled", "priority")


@admin.register(NotificationAuditLog)
class NotificationAuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "notification", "ip_address")
    list_filter = ("action",)
    search_fields = ("actor__email", "notification__recipient")
    readonly_fields = ("created_at", "metadata")
    date_hierarchy = "created_at"
