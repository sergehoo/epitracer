from django.contrib import admin

from .models import Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "channel", "recipient", "status", "provider", "attempts")
    list_filter = ("channel", "status", "provider")
    search_fields = ("recipient", "provider_id")
    date_hierarchy = "created_at"
