from django.db import transaction
from django.utils import timezone

from monitoring.models import MonitorCheck, ServiceMonitor

from .models import Incident


@transaction.atomic
def update_incident_for_check(check):
    # Serialize incident updates for this monitor on PostgreSQL.
    monitor = ServiceMonitor.objects.select_for_update().get(
        pk=check.monitor_id
    )

    # Ignore older results if a newer check already exists.
    latest_check = monitor.checks.order_by(
        "-checked_at", "-id"
    ).first()

    if latest_check is None or latest_check.pk != check.pk:
        return None

    open_incident = Incident.objects.filter(
        monitor=monitor,
        status=Incident.Status.OPEN,
    ).first()

    if check.status in (
        MonitorCheck.Status.DOWN,
        MonitorCheck.Status.ERROR,
    ):
        if open_incident is not None:
            return open_incident

        return Incident.objects.create(
            monitor=monitor,
            title=f"Service unavailable: {monitor.name}"[:200],
            opening_check=check,
        )

    if (
        check.status == MonitorCheck.Status.UP
        and open_incident is not None
    ):
        open_incident.status = Incident.Status.RESOLVED
        open_incident.recovery_check = check
        open_incident.resolved_at = timezone.now()

        open_incident.save(
            update_fields=[
                "status",
                "recovery_check",
                "resolved_at",
            ]
        )

        return open_incident

    return None