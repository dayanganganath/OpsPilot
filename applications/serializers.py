from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

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
    application = serializers.PrimaryKeyRelatedField(
        queryset=Application.objects.none(),
    )

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

        read_only_fields = [
            "id",
            "application_name",
            "created_at",
            "updated_at",
        ]

        validators = [
            UniqueTogetherValidator(
                queryset=Environment.objects.all(),
                fields=["application", "kind"],
                message=(
                    "This application already has an environment "
                    "of this kind."
                ),
            )
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")

        if request is not None and request.user.is_authenticated:
            self.fields["application"].queryset = (
                Application.objects.filter(owner=request.user)
            )

    def validate_application(self, value):
        if (
            self.instance is not None
            and value.pk != self.instance.application_id
        ):
            raise serializers.ValidationError(
                "An existing environment cannot be moved "
                "to another application."
            )

        return value