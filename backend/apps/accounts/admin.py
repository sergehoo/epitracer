from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import LoginEvent, Organization, Role, RoleAssignment, TrustedDevice, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_locked", "mfa_enabled", "last_login")
    list_filter = ("is_active", "is_locked", "mfa_enabled", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("EpidemiTracker", {"fields": ("phone", "job_title", "avatar", "mfa_enabled", "mfa_enforced", "is_locked")}),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "code", "parent")
    list_filter = ("type",)
    search_fields = ("name", "code")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_system")
    list_filter = ("is_system",)


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "organization", "is_active", "granted_by", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("user__email", "role__code")


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "email_attempted", "success", "ip_address", "failure_reason")
    list_filter = ("success",)
    search_fields = ("email_attempted", "ip_address")
    date_hierarchy = "created_at"


@admin.register(TrustedDevice)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "device_id", "last_seen_at")
    search_fields = ("user__email", "label", "device_id")
