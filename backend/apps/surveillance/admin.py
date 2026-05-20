from django.contrib import admin

from .models import HealthAlert


@admin.register(HealthAlert)
class HealthAlertAdmin(admin.ModelAdmin):
    list_display = ("created_at", "code", "title", "severity", "status", "disease", "entry_point")
    list_filter = ("severity", "status", "disease")
    search_fields = ("code", "title", "description")
    date_hierarchy = "created_at"
