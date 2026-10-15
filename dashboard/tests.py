from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from applications.models import Application, Environment
from incidents.models import Incident
from monitoring.models import MonitorCheck, ServiceMonitor


class DashboardSummaryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="dash-owner"
        )
        cls.other = User.objects.create_user(
            username="dash-other"
        )

        cls.application = Application.objects.create(
            name="Dashboard API",
            slug="dashboard-api",
            owner=cls.owner,
        )

        cls.environment = Environment.objects.create(
            application=cls.application,
            kind=Environment.Kind.DEVELOPMENT,
        )

        cls.monitor = ServiceMonitor.objects.create(
            environment=cls.environment,
            name="Dashboard Monitor",
            url="https://example.com/health/",
        )

    def setUp(self):
        self.url = "/api/dashboard/summary/"
        self.client.force_authenticate(user=self.owner)

    def create_check(self, check_status, monitor=None):
        monitor = monitor or self.monitor

        codes = {
            MonitorCheck.Status.UP: 200,
            MonitorCheck.Status.DOWN: 503,
            MonitorCheck.Status.ERROR: None,
        }

        return MonitorCheck.objects.create(
            monitor=monitor,
            checked_url=monitor.url,
            expected_status_code=200,
            status=check_status,
            status_code=codes[check_status],
            response_time_ms=10,
        )

    def test_anonymous_access_is_blocked(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_user_without_records_gets_zero_counts(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            "total_applications": 0,
            "total_monitors": 0,
            "active_monitors": 0,
            "up_monitors": 0,
            "down_monitors": 0,
            "error_monitors": 0,
            "unchecked_monitors": 0,
            "open_incidents": 0,
            "resolved_incidents": 0,
        })

    def test_unchecked_monitor_counts(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            "total_applications": 1,
            "total_monitors": 1,
            "active_monitors": 1,
            "up_monitors": 0,
            "down_monitors": 0,
            "error_monitors": 0,
            "unchecked_monitors": 1,
            "open_incidents": 0,
            "resolved_incidents": 0,
        })

    def test_only_latest_check_counts(self):
        for check_status in (
            MonitorCheck.Status.DOWN,
            MonitorCheck.Status.ERROR,
            MonitorCheck.Status.UP,
        ):
            with self.subTest(status=check_status):
                self.create_check(check_status)

                response = self.client.get(self.url)

                self.assertEqual(response.status_code, 200)

                for value in ("up", "down", "error"):
                    self.assertEqual(
                        response.data[f"{value}_monitors"],
                        int(value == check_status),
                    )

                self.assertEqual(
                    response.data["unchecked_monitors"],
                    0,
                )

    def test_other_users_records_are_excluded(self):
        application = Application.objects.create(
            name="Other API",
            slug="other-api",
            owner=self.other,
        )

        environment = Environment.objects.create(
            application=application,
            kind=Environment.Kind.PRODUCTION,
        )

        monitor = ServiceMonitor.objects.create(
            environment=environment,
            name="Other Monitor",
            url="https://example.com/other/",
        )

        check = self.create_check(
            MonitorCheck.Status.DOWN,
            monitor=monitor,
        )

        Incident.objects.create(
            monitor=monitor,
            title="Other private incident",
            opening_check=check,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            "total_applications": 1,
            "total_monitors": 1,
            "active_monitors": 1,
            "up_monitors": 0,
            "down_monitors": 0,
            "error_monitors": 0,
            "unchecked_monitors": 1,
            "open_incidents": 0,
            "resolved_incidents": 0,
        })

    def test_inactive_resources_exclude_monitor_status(self):
        self.create_check(MonitorCheck.Status.UP)

        for resource in (
            self.monitor,
            self.environment,
            self.application,
        ):
            with self.subTest(
                resource=type(resource).__name__
            ):
                resource.is_active = False
                resource.save(update_fields=["is_active"])

                response = self.client.get(self.url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.data["total_monitors"],
                    1,
                )
                self.assertEqual(
                    response.data["active_monitors"],
                    0,
                )

                for key in (
                    "up_monitors",
                    "down_monitors",
                    "error_monitors",
                    "unchecked_monitors",
                ):
                    self.assertEqual(
                        response.data[key],
                        0,
                    )

                resource.is_active = True
                resource.save(update_fields=["is_active"])

    def test_open_and_resolved_incident_counts(self):
        failure = self.create_check(
            MonitorCheck.Status.DOWN
        )
        recovery = self.create_check(
            MonitorCheck.Status.UP
        )

        Incident.objects.create(
            monitor=self.monitor,
            title="Resolved outage",
            status=Incident.Status.RESOLVED,
            opening_check=failure,
            recovery_check=recovery,
            resolved_at=timezone.now(),
        )

        new_failure = self.create_check(
            MonitorCheck.Status.DOWN
        )

        Incident.objects.create(
            monitor=self.monitor,
            title="New outage",
            opening_check=new_failure,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["open_incidents"],
            1,
        )
        self.assertEqual(
            response.data["resolved_incidents"],
            1,
        )
        self.assertEqual(
            response.data["down_monitors"],
            1,
        )