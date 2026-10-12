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
        read_only_fields = fields


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