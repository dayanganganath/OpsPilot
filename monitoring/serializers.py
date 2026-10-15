from rest_framework import serializers

from .models import MonitorCheck, ServiceMonitor


class ServiceMonitorSerializer(serializers.ModelSerializer):
    environment_name = serializers.CharField(
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
        read_only_fields = fields


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