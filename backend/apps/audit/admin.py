from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "summary", "ip_address")
    list_filter = ("action",)
    search_fields = ("summary", "ip_address", "request_id")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in AuditLog._meta.fields]
