from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from applications.models import Application, Environment

from .models import MonitorCheck, ServiceMonitor


class MonitorWriteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(username="monitor-owner")
        cls.other = User.objects.create_user(username="monitor-other")

        application = Application.objects.create(
            name="Owner API",
            slug="monitor-owner-api",
            owner=cls.owner,
        )

        other_application = Application.objects.create(
            name="Other API",
            slug="monitor-other-api",
            owner=cls.other,
        )

        cls.environment = Environment.objects.create(
            application=application,
            kind=Environment.Kind.DEVELOPMENT,
        )

        cls.second_environment = Environment.objects.create(
            application=application,
            kind=Environment.Kind.STAGING,
        )

        cls.other_environment = Environment.objects.create(
            application=other_application,
            kind=Environment.Kind.DEVELOPMENT,
        )

        cls.monitor = ServiceMonitor.objects.create(
            environment=cls.environment,
            name="Original Monitor",
            url="https://example.com/health/",
        )

    def setUp(self):
        self.client.force_authenticate(user=self.owner)
        self.list_url = "/api/monitors/"
        self.detail_url = f"/api/monitors/{self.monitor.pk}/"

    def test_owner_can_create_monitor(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "New Monitor",
                "environment": self.environment.pk,
                "url": "https://example.com/status/",
                "expected_status_code": 204,
                "check_interval_seconds": 120,
                "timeout_seconds": 15,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        saved = ServiceMonitor.objects.get(pk=response.data["id"])

        self.assertEqual(saved.environment_id, self.environment.pk)
        self.assertEqual(saved.expected_status_code, 204)
        self.assertEqual(saved.check_interval_seconds, 120)
        self.assertEqual(saved.timeout_seconds, 15)
        self.assertFalse(MonitorCheck.objects.exists())

    def test_owner_can_edit_without_changing_saved_history(self):
        check = MonitorCheck.objects.create(
            monitor=self.monitor,
            checked_url=self.monitor.url,
            expected_status_code=200,
            status=MonitorCheck.Status.UP,
            status_code=200,
            response_time_ms=20,
        )

        response = self.client.patch(
            self.detail_url,
            {
                "name": "Updated Monitor",
                "url": "https://example.com/new-health/",
                "expected_status_code": 204,
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.monitor.refresh_from_db()
        check.refresh_from_db()

        self.assertEqual(self.monitor.name, "Updated Monitor")
        self.assertEqual(self.monitor.expected_status_code, 204)
        self.assertFalse(self.monitor.is_active)
        self.assertEqual(
            check.checked_url,
            "https://example.com/health/",
        )
        self.assertEqual(check.expected_status_code, 200)
        self.assertEqual(check.monitor_id, self.monitor.pk)

    def test_cannot_create_for_another_users_environment(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Unauthorized Monitor",
                "environment": self.other_environment.pk,
                "url": "https://example.com/health/",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("environment", response.data)
        self.assertEqual(ServiceMonitor.objects.count(), 1)

    def test_other_user_cannot_edit_monitor(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            self.detail_url,
            {"name": "Unauthorized change"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.monitor.refresh_from_db()
        self.assertEqual(self.monitor.name, "Original Monitor")

    def test_existing_monitor_cannot_change_environment(self):
        response = self.client.patch(
            self.detail_url,
            {"environment": self.second_environment.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("environment", response.data)

        self.monitor.refresh_from_db()
        self.assertEqual(
            self.monitor.environment_id,
            self.environment.pk,
        )

    def test_duplicate_name_in_same_environment_is_rejected(self):
        response = self.client.post(
            self.list_url,
            {
                "name": self.monitor.name,
                "environment": self.environment.pk,
                "url": "https://example.com/another/",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(ServiceMonitor.objects.count(), 1)

    def test_invalid_field_values_are_rejected(self):
        invalid_values = [
            ("name", "X"),
            ("expected_status_code", 99),
            ("expected_status_code", 600),
            ("check_interval_seconds", 29),
            ("check_interval_seconds", 86401),
            ("timeout_seconds", 0),
            ("timeout_seconds", 31),
        ]

        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                response = self.client.patch(
                    self.detail_url,
                    {field: value},
                    format="json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

        self.monitor.refresh_from_db()

        self.assertEqual(self.monitor.name, "Original Monitor")
        self.assertEqual(self.monitor.expected_status_code, 200)
        self.assertEqual(self.monitor.check_interval_seconds, 60)
        self.assertEqual(self.monitor.timeout_seconds, 10)

    def test_invalid_or_credential_urls_are_rejected(self):
        invalid_urls = [
            "not-a-url",
            "ftp://example.com/health/",
            "https://user:password@example.com/health/",
        ]

        for url in invalid_urls:
            with self.subTest(url=url):
                response = self.client.patch(
                    self.detail_url,
                    {"url": url},
                    format="json",
                )

                self.assertEqual(response.status_code, 400)
                self.assertIn("url", response.data)

        self.monitor.refresh_from_db()
        self.assertEqual(
            self.monitor.url,
            "https://example.com/health/",
        )

    def test_anonymous_writes_are_blocked(self):
        self.client.force_authenticate(user=None)

        create = self.client.post(
            self.list_url,
            {
                "name": "Anonymous Monitor",
                "environment": self.environment.pk,
                "url": "https://example.com/health/",
            },
            format="json",
        )

        update = self.client.patch(
            self.detail_url,
            {"is_active": False},
            format="json",
        )

        self.assertEqual(create.status_code, 403)
        self.assertEqual(update.status_code, 403)
        self.assertEqual(ServiceMonitor.objects.count(), 1)

        self.monitor.refresh_from_db()
        self.assertTrue(self.monitor.is_active)

    def test_delete_is_not_allowed(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            ServiceMonitor.objects.filter(
                pk=self.monitor.pk
            ).exists()
        )