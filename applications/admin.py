from django.contrib import admin

from .models import Application, Environment


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "owner",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "slug",
        "description",
        "owner__username",
    )
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("owner",)


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "kind",
        "base_url",
        "is_active",
    )
    list_filter = ("kind", "is_active")
    search_fields = (
        "application__name",
        "application__slug",
        "base_url",
    )
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("application",)