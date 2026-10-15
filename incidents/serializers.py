from rest_framework import serializers

from .models import Incident


class IncidentSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(
        source="monitor.name",
        read_only=True,
    )
    application_name = serializers.CharField(
        source="monitor.environment.application.name",
        read_only=True,
    )

    class Meta:
        model = Incident
        fields = [
            "id",
            "title",
            "monitor",
            "monitor_name",
            "application_name",
            "status",
            "opening_check",
            "recovery_check",
            "opened_at",
            "resolved_at",
        ]
        read_only_fields = fields