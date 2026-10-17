import logging
from datetime import timedelta

from celery import current_app, shared_task
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from redis import Redis
from redis.exceptions import LockError

from .models import MonitorCheck, ServiceMonitor
from .services import run_monitor_check


logger = logging.getLogger(__name__)


def active_monitors():
    return ServiceMonitor.objects.filter(
        is_active=True,
        environment__is_active=True,
        environment__application__is_active=True,
    ).select_related(
        "environment",
        "environment__application",
    )


def check_is_due(last_checked_at, interval_seconds):
    if last_checked_at is None:
        return True

    next_check_at = last_checked_at + timedelta(
        seconds=interval_seconds,
    )

    return timezone.now() >= next_check_at


@shared_task(ignore_result=True, time_limit=60)
def check_monitor(monitor_id):
    redis_client = Redis.from_url(
        current_app.conf.broker_url,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    lock = redis_client.lock(
        f"opspilot:scheduled-monitor:{monitor_id}",
        timeout=120,
        blocking=False,
    )

    try:
        if not lock.acquire():
            return {"skipped": "already_running"}

        try:
            monitor = active_monitors().filter(
                pk=monitor_id,
            ).first()

            if monitor is None:
                return {"skipped": "inactive_or_missing"}

            latest_check = (
                monitor.checks
                .order_by("-checked_at", "-id")
                .first()
            )

            last_checked_at = (
                latest_check.checked_at
                if latest_check is not None
                else None
            )

            if not check_is_due(
                last_checked_at,
                monitor.check_interval_seconds,
            ):
                return {"skipped": "not_due"}

            result = run_monitor_check(monitor)

            logger.info(
                "Scheduled check saved: monitor=%s check=%s status=%s",
                monitor.pk,
                result.pk,
                result.status,
            )

            return {
                "monitor_id": monitor.pk,
                "check_id": result.pk,
                "status": result.status,
            }

        finally:
            try:
                lock.release()
            except LockError:
                logger.warning(
                    "Scheduled lock expired: monitor=%s",
                    monitor_id,
                )

    finally:
        redis_client.close()


@shared_task(ignore_result=True)
def dispatch_due_monitors():
    latest_check = (
        MonitorCheck.objects
        .filter(monitor_id=OuterRef("pk"))
        .order_by("-checked_at", "-id")
    )

    monitors = (
        active_monitors()
        .annotate(
            last_checked_at=Subquery(
                latest_check.values("checked_at")[:1]
            )
        )
        .values(
            "id",
            "check_interval_seconds",
            "last_checked_at",
        )
    )

    queued = 0

    for monitor in monitors.iterator():
        if check_is_due(
            monitor["last_checked_at"],
            monitor["check_interval_seconds"],
        ):
            check_monitor.apply_async(
                args=[monitor["id"]],
                expires=30,
            )
            queued += 1

    return {"queued": queued}