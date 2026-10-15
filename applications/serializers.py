from rest_framework import serializers

from .models import Application, Environment


class ApplicationSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True,
    )

    class Meta:
        model = Application

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "repository_url",
            "owner_username",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "owner_username",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()

        if len(value) < 2:
            raise serializers.ValidationError(
                "Application name must contain at least 2 characters."
            )

        return value


class EnvironmentSerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(
        source="application.name",
        read_only=True,
    )

    class Meta:
        model = Environment

        fields = [
            "id",
            "application",
            "application_name",
            "kind",
            "base_url",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields