from django.contrib import admin

from .models import ServiceMonitor


@admin.register(ServiceMonitor)
class ServiceMonitorAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "environment",
        "expected_status_code",
        "check_interval_seconds",
        "timeout_seconds",
        "is_active",
    )
    list_filter = (
        "is_active",
        "environment__kind",
    )
    search_fields = (
        "name",
        "url",
        "environment__application__name",
    )
    readonly_fields = ("created_at", "updated_at")
    list_select_related = (
        "environment",
        "environment__application",
    )