from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from applications.models import Application, Environment

from .models import MonitorCheck, ServiceMonitor


class MonitoringTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(username="owner")
        cls.other_user = User.objects.create_user(username="other")

        application = Application.objects.create(
            name="Test API",
            slug="test-api",
            owner=cls.owner,
        )

        environment = Environment.objects.create(
            application=application,
            kind=Environment.Kind.DEVELOPMENT,
        )

        cls.monitor = ServiceMonitor.objects.create(
            environment=environment,
            name="Health Check",
            url="https://example.com/health/",
        )

    def setUp(self):
        self.client.force_authenticate(user=self.owner)

        self.check_url = (
            f"/api/monitors/{self.monitor.pk}/check-now/"
        )
        self.history_url = (
            f"/api/monitors/{self.monitor.pk}/history/"
        )

    @patch("monitoring.services.httpx.Client")
    def test_successful_check_is_saved(self, mock_client):
        client = mock_client.return_value.__enter__.return_value
        response = client.stream.return_value.__enter__.return_value
        response.status_code = 200

        result = self.client.post(
            self.check_url, {}, format="json"
        )

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["status"], "up")
        self.assertEqual(result.data["status_code"], 200)

        saved = MonitorCheck.objects.get()

        self.assertEqual(saved.monitor_id, self.monitor.pk)
        self.assertEqual(saved.checked_url, self.monitor.url)
        self.assertEqual(saved.expected_status_code, 200)
        self.assertEqual(saved.status, MonitorCheck.Status.UP)
        self.assertEqual(saved.error_message, "")
        self.assertGreaterEqual(saved.response_time_ms, 0)

        client.stream.assert_called_once_with(
            "GET", self.monitor.url
        )

    @patch("monitoring.services.httpx.Client")
    def test_unexpected_status_is_saved_as_down(self, mock_client):
        client = mock_client.return_value.__enter__.return_value
        response = client.stream.return_value.__enter__.return_value
        response.status_code = 503

        result = self.client.post(
            self.check_url, {}, format="json"
        )

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["status"], "down")

        saved = MonitorCheck.objects.get()

        self.assertEqual(saved.status_code, 503)
        self.assertEqual(saved.status, MonitorCheck.Status.DOWN)

    @patch("monitoring.services.httpx.Client")
    def test_timeout_is_saved_as_error(self, mock_client):
        client = mock_client.return_value.__enter__.return_value
        client.stream.side_effect = httpx.ReadTimeout("Test timeout")

        result = self.client.post(
            self.check_url, {}, format="json"
        )

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["status"], "error")

        saved = MonitorCheck.objects.get()

        self.assertIsNone(saved.status_code)
        self.assertEqual(saved.error_message, "Request timed out.")

    @patch("monitoring.services.httpx.Client")
    def test_connection_error_is_saved(self, mock_client):
        client = mock_client.return_value.__enter__.return_value
        client.stream.side_effect = httpx.ConnectError("Test error")

        result = self.client.post(
            self.check_url, {}, format="json"
        )

        self.assertEqual(result.status_code, 201)

        saved = MonitorCheck.objects.get()

        self.assertEqual(saved.status, MonitorCheck.Status.ERROR)
        self.assertIsNone(saved.status_code)
        self.assertEqual(
            saved.error_message,
            "Could not connect to the service.",
        )

    @patch("monitoring.services.httpx.Client")
    def test_anonymous_access_is_blocked(self, mock_client):
        self.client.force_authenticate(user=None)

        result = self.client.post(
            self.check_url, {}, format="json"
        )
        history = self.client.get(self.history_url)

        self.assertEqual(result.status_code, 403)
        self.assertEqual(history.status_code, 403)
        self.assertFalse(MonitorCheck.objects.exists())

        mock_client.assert_not_called()

    @patch("monitoring.services.httpx.Client")
    def test_other_user_cannot_access_monitor(self, mock_client):
        self.client.force_authenticate(user=self.other_user)

        result = self.client.post(
            self.check_url, {}, format="json"
        )
        history = self.client.get(self.history_url)
        monitors = self.client.get("/api/monitors/")

        self.assertEqual(result.status_code, 404)
        self.assertEqual(history.status_code, 404)
        self.assertEqual(monitors.status_code, 200)
        self.assertEqual(monitors.data, [])
        self.assertFalse(MonitorCheck.objects.exists())

        mock_client.assert_not_called()

    @patch("monitoring.services.httpx.Client")
    def test_inactive_resources_block_checks(self, mock_client):
        resources = [
            self.monitor,
            self.monitor.environment,
            self.monitor.environment.application,
        ]

        for resource in resources:
            with self.subTest(resource=type(resource).__name__):
                resource.is_active = False
                resource.save(update_fields=["is_active"])

                result = self.client.post(
                    self.check_url, {}, format="json"
                )

                self.assertEqual(result.status_code, 400)
                self.assertFalse(MonitorCheck.objects.exists())
                mock_client.assert_not_called()

                resource.is_active = True
                resource.save(update_fields=["is_active"])

    @patch("monitoring.services.httpx.Client")
    def test_history_returns_latest_check_first(self, mock_client):
        client = mock_client.return_value.__enter__.return_value
        response = client.stream.return_value.__enter__.return_value
        response.status_code = 200

        first = self.client.post(
            self.check_url, {}, format="json"
        )
        second = self.client.post(
            self.check_url, {}, format="json"
        )
        history = self.client.get(self.history_url)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(history.status_code, 200)

        self.assertEqual(
            [item["id"] for item in history.data],
            [second.data["id"], first.data["id"]],
        )