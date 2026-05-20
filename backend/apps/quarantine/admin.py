from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import DailyCheck, FollowUpVisit, QuarantineRecord


class DailyCheckInline(admin.TabularInline):
    model = DailyCheck
    extra = 0


class FollowUpVisitInline(admin.TabularInline):
    model = FollowUpVisit
    extra = 0


@admin.register(QuarantineRecord)
class QuarantineRecordAdmin(GISModelAdmin):
    list_display = ("traveler", "disease", "status", "started_on", "expected_end_on", "actual_end_on")
    list_filter = ("status", "disease")
    search_fields = ("traveler__public_id", "traveler__last_name", "investigation_ref")
    inlines = [DailyCheckInline, FollowUpVisitInline]
