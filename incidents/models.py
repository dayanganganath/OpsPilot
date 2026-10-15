from django.db import models

from monitoring.models import MonitorCheck, ServiceMonitor


class Incident(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    monitor = models.ForeignKey(
        ServiceMonitor,
        on_delete=models.CASCADE,
        related_name="incidents",
    )

    title = models.CharField(max_length=200)

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    opening_check = models.ForeignKey(
        MonitorCheck,
        on_delete=models.PROTECT,
        related_name="opened_incidents",
    )

    recovery_check = models.ForeignKey(
        MonitorCheck,
        on_delete=models.PROTECT,
        related_name="resolved_incidents",
        null=True,
        blank=True,
    )

    opened_at = models.DateTimeField(auto_now_add=True)

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-opened_at", "-id"]

        constraints = [
            models.UniqueConstraint(
                fields=["monitor"],
                condition=models.Q(status="open"),
                name="one_open_incident_per_monitor",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="open",
                        resolved_at__isnull=True,
                        recovery_check__isnull=True,
                    )
                    | models.Q(
                        status="resolved",
                        resolved_at__isnull=False,
                        recovery_check__isnull=False,
                    )
                ),
                name="incident_resolution_fields_match_status",
            ),
        ]

    def __str__(self):
        return f"{self.title} — {self.get_status_display()}"