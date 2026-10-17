from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from applications.models import Application, Environment

from .models import MonitorCheck, ServiceMonitor
from .tasks import (
    check_is_due,
    check_monitor,
    dispatch_due_monitors,
)


class ScheduledMonitoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        owner = get_user_model().objects.create_user(
            username="scheduled-owner",
        )

        application = Application.objects.create(
            name="Scheduled API",
            slug="scheduled-api",
            owner=owner,
        )

        cls.environment = Environment.objects.create(
            application=application,
            kind=Environment.Kind.DEVELOPMENT,
        )

        cls.monitor = ServiceMonitor.objects.create(
            environment=cls.environment,
            name="Scheduled Health",
            url="https://example.com/health/",
            check_interval_seconds=60,
        )

    def setUp(self):
        redis_patch = patch(
            "monitoring.tasks.Redis.from_url"
        )
        self.redis_factory = redis_patch.start()
        self.addCleanup(redis_patch.stop)

        self.redis_client = self.redis_factory.return_value
        self.lock = self.redis_client.lock.return_value
        self.lock.acquire.return_value = True

        service_patch = patch(
            "monitoring.tasks.run_monitor_check"
        )
        self.run_check = service_patch.start()
        self.addCleanup(service_patch.stop)

        self.run_check.return_value = SimpleNamespace(
            pk=99,
            status="up",
        )

    def save_recent_check(self, monitor):
        return MonitorCheck.objects.create(
            monitor=monitor,
            checked_url=monitor.url,
            expected_status_code=200,
            status=MonitorCheck.Status.UP,
            status_code=200,
            response_time_ms=10,
        )

    def test_due_calculation(self):
        now = timezone.now()

        with patch(
            "monitoring.tasks.timezone.now",
            return_value=now,
        ):
            self.assertTrue(check_is_due(None, 60))

            self.assertFalse(
                check_is_due(
                    now - timedelta(seconds=59),
                    60,
                )
            )

            self.assertTrue(
                check_is_due(
                    now - timedelta(seconds=60),
                    60,
                )
            )

    def test_dispatch_only_queues_due_active_monitors(self):
        recent = ServiceMonitor.objects.create(
            environment=self.environment,
            name="Recently Checked",
            url="https://example.com/recent/",
            check_interval_seconds=60,
        )
        self.save_recent_check(recent)

        ServiceMonitor.objects.create(
            environment=self.environment,
            name="Disabled Monitor",
            url="https://example.com/disabled/",
            is_active=False,
        )

        with patch(
            "monitoring.tasks.check_monitor.apply_async"
        ) as publish:
            result = dispatch_due_monitors()

        self.assertEqual(result, {"queued": 1})
        publish.assert_called_once_with(
            args=[self.monitor.pk],
            expires=30,
        )
        self.run_check.assert_not_called()

    def test_busy_lock_skips_check(self):
        self.lock.acquire.return_value = False

        result = check_monitor(self.monitor.pk)

        self.assertEqual(
            result,
            {"skipped": "already_running"},
        )
        self.run_check.assert_not_called()
        self.lock.release.assert_not_called()
        self.redis_client.close.assert_called_once()

    def test_inactive_resources_skip_check(self):
        resources = [
            self.monitor,
            self.environment,
            self.environment.application,
        ]

        for resource in resources:
            with self.subTest(
                model=resource.__class__.__name__,
            ):
                resource.is_active = False
                resource.save(update_fields=["is_active"])

                result = check_monitor(self.monitor.pk)

                self.assertEqual(
                    result,
                    {"skipped": "inactive_or_missing"},
                )

                resource.is_active = True
                resource.save(update_fields=["is_active"])

        self.run_check.assert_not_called()
        self.assertEqual(
            self.lock.release.call_count,
            len(resources),
        )

    def test_recent_check_is_not_run_again(self):
        self.save_recent_check(self.monitor)

        result = check_monitor(self.monitor.pk)

        self.assertEqual(
            result,
            {"skipped": "not_due"},
        )
        self.run_check.assert_not_called()
        self.lock.release.assert_called_once()
        self.redis_client.close.assert_called_once()

    def test_due_monitor_runs_check(self):
        result = check_monitor(self.monitor.pk)

        self.assertEqual(
            result,
            {
                "monitor_id": self.monitor.pk,
                "check_id": 99,
                "status": "up",
            },
        )

        self.run_check.assert_called_once()
        checked_monitor = self.run_check.call_args.args[0]

        self.assertEqual(
            checked_monitor.pk,
            self.monitor.pk,
        )
        self.lock.release.assert_called_once()
        self.redis_client.close.assert_called_once()

    def test_service_failure_releases_lock(self):
        self.run_check.side_effect = RuntimeError(
            "Test service failure",
        )

        with self.assertRaisesMessage(
            RuntimeError,
            "Test service failure",
        ):
            check_monitor(self.monitor.pk)

        self.lock.release.assert_called_once()
        self.redis_client.close.assert_called_once()