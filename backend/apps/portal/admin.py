from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from simple_history.admin import SimpleHistoryAdmin

from .models import PublicNotice
from .services import archive_notice, publish_notice


@admin.register(PublicNotice)
class PublicNoticeAdmin(SimpleHistoryAdmin):
    list_display = (
        "title",
        "kind",
        "alert_level",
        "status",
        "disease",
        "valid_from",
        "valid_until",
    )
    list_filter = ("kind", "status", "alert_level", "disease")
    search_fields = ("title", "summary", "body")
    filter_horizontal = ("countries",)
    raw_id_fields = ("source_alert",)
    readonly_fields = ("status", "published_at", "published_by")
    actions = ["publish_selected", "archive_selected"]

    @admin.action(description="Publier sur le portail")
    def publish_selected(self, request, queryset):
        self._apply(request, queryset, publish_notice)

    @admin.action(description="Archiver (retirer du portail)")
    def archive_selected(self, request, queryset):
        self._apply(request, queryset, archive_notice)

    def _apply(self, request, queryset, service):
        done = 0
        for notice in queryset:
            try:
                service(notice, request.user)
                done += 1
            except (PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"{notice.title} : {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"{done} annonce(s) mise(s) à jour.", level=messages.SUCCESS)
