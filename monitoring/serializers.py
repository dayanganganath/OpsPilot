from urllib.parse import urlsplit

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from applications.models import Environment

from .models import MonitorCheck, ServiceMonitor


class ServiceMonitorSerializer(serializers.ModelSerializer):
    environment = serializers.PrimaryKeyRelatedField(
        queryset=Environment.objects.none(),
    )

    environment_name = serializers.StringRelatedField(
        source="environment",
        read_only=True,
    )

    class Meta:
        model = ServiceMonitor

        fields = [
            "id",
            "name",
            "environment",
            "environment_name",
            "url",
            "expected_status_code",
            "check_interval_seconds",
            "timeout_seconds",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "environment_name",
            "created_at",
            "updated_at",
        ]

        validators = [
            UniqueTogetherValidator(
                queryset=ServiceMonitor.objects.all(),
                fields=["environment", "name"],
                message=(
                    "This environment already has a monitor "
                    "with this name."
                ),
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request is not None and request.user.is_authenticated:
            self.fields["environment"].queryset = (
                Environment.objects.filter(
                    application__owner=request.user
                ).select_related("application")
            )

    def validate_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Monitor name must contain at least 2 characters."
            )

        return value

    def validate_environment(self, value):
        if (
            self.instance is not None
            and value.pk != self.instance.environment_id
        ):
            raise serializers.ValidationError(
                "An existing monitor cannot be moved "
                "to another environment."
            )

        return value

    def validate_url(self, value):
        parts = urlsplit(value)

        if parts.scheme.lower() not in ("http", "https"):
            raise serializers.ValidationError(
                "Use an HTTP or HTTPS URL."
            )

        if parts.username is not None or parts.password is not None:
            raise serializers.ValidationError(
                "Monitoring URLs must not contain login credentials."
            )

        return value


class MonitorCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorCheck

        fields = [
            "id",
            "monitor",
            "checked_url",
            "expected_status_code",
            "status",
            "status_code",
            "response_time_ms",
            "error_message",
            "checked_at",
        ]

        read_only_fields = fields