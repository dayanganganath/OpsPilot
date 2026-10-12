from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

from applications.models import Environment


class ServiceMonitor(models.Model):
    environment = models.ForeignKey(
        Environment,
        on_delete=models.CASCADE,
        related_name="monitors",
    )

    name = models.CharField(max_length=150)
    url = models.URLField(max_length=2048)

    expected_status_code = models.PositiveSmallIntegerField(
        default=200,
        validators=[
            MinValueValidator(100),
            MaxValueValidator(599),
        ],
    )

    check_interval_seconds = models.PositiveIntegerField(
        default=60,
        validators=[
            MinValueValidator(30),
            MaxValueValidator(86400),
        ],
    )

    timeout_seconds = models.PositiveSmallIntegerField(
        default=10,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(30),
        ],
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["environment", "name"],
                name="unique_monitor_name_per_environment",
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.environment}"

class MonitorCheck(models.Model):
    class Status(models.TextChoices):
        UP = "up", "Up"
        DOWN = "down", "Down"
        ERROR = "error", "Error"

    monitor = models.ForeignKey(
        ServiceMonitor,
        on_delete=models.CASCADE,
        related_name="checks",
    )

    checked_url = models.URLField(max_length=2048)
    expected_status_code = models.PositiveSmallIntegerField()

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
    )

    status_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    response_time_ms = models.FloatField(
        validators=[MinValueValidator(0)],
    )

    error_message = models.CharField(
        max_length=500,
        blank=True,
    )

    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_at", "-id"]
        indexes = [
            models.Index(
                fields=["monitor", "-checked_at"],
                name="monitor_check_time_idx",
            )
        ]

    def __str__(self):
        return f"{self.monitor.name} — {self.get_status_display()}"