from django.conf import settings
from django.db import models


class Application(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    repository_url = models.URLField(blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_applications",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name

class Environment(models.Model):
    class Kind(models.TextChoices):
        DEVELOPMENT = "development", "Development"
        STAGING = "staging", "Staging"
        PRODUCTION = "production", "Production"

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name="environments",
    )

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
    )

    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["application__name", "kind"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "kind"],
                name="unique_environment_kind_per_application",
            )
        ]

    def __str__(self):
        return (
            f"{self.application.name} "
            f"— {self.get_kind_display()}"
        )