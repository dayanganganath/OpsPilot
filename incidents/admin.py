from django.contrib import admin

from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "monitor",
        "status",
        "opened_at",
        "resolved_at",
    )

    list_filter = ("status",)

    search_fields = (
        "title",
        "monitor__name",
        "monitor__environment__application__name",
    )

    readonly_fields = (
        "monitor",
        "title",
        "status",
        "opening_check",
        "recovery_check",
        "opened_at",
        "resolved_at",
    )

    list_select_related = (
        "monitor",
        "monitor__environment",
        "monitor__environment__application",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False