from django.contrib import admin

from .models import PageVisit


@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "portal", "path", "country_code",
        "ip_address", "is_bot", "user",
    )
    list_filter = ("portal", "is_bot", "country_code")
    search_fields = ("path", "ip_address", "session_id", "country_code", "user__email")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in PageVisit._meta.fields]
