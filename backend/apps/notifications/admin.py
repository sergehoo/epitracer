from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Notification, NotificationAuditLog, NotificationProviderConfig,
    NotificationStatus, NotificationTemplate,
)
from .services.audit import Actions, log_action


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "disease", "channels_str")
    list_filter = ("is_active", "disease")
    search_fields = ("code", "name", "description")
    autocomplete_fields = ("disease",)

    @admin.display(description="Canaux")
    def channels_str(self, obj):
        return ", ".join(obj.channels or [])


# ---------------------------------------------------------------------------
# Filtre rapide : "Échecs récents" (FAILED dernières 24h)
# ---------------------------------------------------------------------------
class RecentFailedFilter(admin.SimpleListFilter):
    title = "Échec récent"
    parameter_name = "recent_failed"

    def lookups(self, request, model_admin):
        return (
            ("24h", "FAILED dernières 24 h"),
            ("7d", "FAILED 7 derniers jours"),
            ("retry_left", "FAILED avec retries restants"),
        )

    def queryset(self, request, queryset):
        from datetime import timedelta
        from django.db.models import F
        now = timezone.now()
        if self.value() == "24h":
            return queryset.filter(
                status=NotificationStatus.FAILED, failed_at__gte=now - timedelta(hours=24),
            )
        if self.value() == "7d":
            return queryset.filter(
                status=NotificationStatus.FAILED, failed_at__gte=now - timedelta(days=7),
            )
        if self.value() == "retry_left":
            return queryset.filter(
                status=NotificationStatus.FAILED, retry_count__lt=F("max_retries"),
            )
        return queryset


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "channel", "provider", "masked_recipient",
        "status_badge", "message_type", "retry_count", "short_error", "sent_by",
    )
    list_filter = (
        RecentFailedFilter,
        "status", "channel", "provider", "direction", "message_type",
    )
    list_select_related = ("traveler", "template", "sent_by")
    search_fields = ("recipient", "normalized_phone", "provider_message_id", "body", "error_message")
    autocomplete_fields = ("traveler", "template", "sent_by")
    date_hierarchy = "created_at"
    readonly_fields = (
        "uuid", "normalized_phone", "provider_message_id", "retry_count",
        "queued_at", "sent_at", "delivered_at", "failed_at", "metadata",
    )
    actions = ["action_retry_failed", "action_cancel"]

    # ── Affichage enrichi ────────────────────────────────────────────────
    @admin.display(description="Statut")
    def status_badge(self, obj):
        color = {
            "sent":      "#10b981",
            "delivered": "#059669",
            "failed":    "#ef4444",
            "queued":    "#3b82f6",
            "pending":   "#6b7280",
            "cancelled": "#9ca3af",
        }.get(obj.status, "#6b7280")
        return format_html(
            '<span style="display:inline-block;padding:2px 8px;border-radius:9999px;'
            'background:{};color:white;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description="Erreur (extrait)")
    def short_error(self, obj):
        if not obj.error_message:
            return "—"
        msg = obj.error_message[:80]
        return format_html(
            '<span title="{}" style="color:#b91c1c;font-size:11px;">{}</span>',
            obj.error_message, msg + ("…" if len(obj.error_message) > 80 else ""),
        )

    # ── Actions de relance ───────────────────────────────────────────────
    @admin.action(description="🔁 Relancer les notifications FAILED sélectionnées")
    def action_retry_failed(self, request, queryset):
        """Re-queue les notifications FAILED / CANCELLED sélectionnées."""
        from .tasks import send_notification_task

        eligible = queryset.filter(
            status__in=(NotificationStatus.FAILED, NotificationStatus.CANCELLED),
        )
        skipped = queryset.count() - eligible.count()
        requeued = 0
        for notif in eligible:
            notif.status = NotificationStatus.QUEUED
            notif.error_message = ""
            notif.queued_at = timezone.now()
            notif.save(update_fields=["status", "error_message", "queued_at", "updated_at"])
            log_action(
                notification=notif, action=Actions.RETRY,
                actor=request.user,
                metadata={"manual_retry": True, "from_django_admin": True},
            )
            send_notification_task.delay(notif.id)
            requeued += 1

        if requeued:
            self.message_user(
                request,
                f"✅ {requeued} notification(s) re-queuée(s) avec succès.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"⚠️ {skipped} notification(s) ignorée(s) (statut non FAILED/CANCELLED).",
                level=messages.WARNING,
            )

    @admin.action(description="🚫 Annuler les notifications sélectionnées (si PENDING/QUEUED)")
    def action_cancel(self, request, queryset):
        eligible = queryset.exclude(
            status__in=(NotificationStatus.SENT, NotificationStatus.DELIVERED),
        )
        n = eligible.update(status=NotificationStatus.CANCELLED, updated_at=timezone.now())
        self.message_user(
            request, f"🚫 {n} notification(s) annulée(s).", level=messages.SUCCESS,
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
