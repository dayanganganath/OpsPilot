from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from applications.models import Application, Environment
from monitoring.models import MonitorCheck, ServiceMonitor
from monitoring.services import run_monitor_check

from .models import Incident


class IncidentLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(
            username="incident-owner"
        )

        application = Application.objects.create(
            name="Incident Test API",
            slug="incident-test-api",
            owner=user,
        )

        environment = Environment.objects.create(
            application=application,
            kind=Environment.Kind.DEVELOPMENT,
        )

        cls.monitor = ServiceMonitor.objects.create(
            environment=environment,
            name="Test Health Check",
            url="https://example.com/health/",
        )

    def run_check(self, status_code=200, error=None):
        with patch("monitoring.services.httpx.Client") as mock:
            client = mock.return_value.__enter__.return_value

            if error is not None:
                client.stream.side_effect = error
            else:
                response = (
                    client.stream.return_value
                    .__enter__.return_value
                )
                response.status_code = status_code

            return run_monitor_check(self.monitor)

    def test_failed_check_opens_incident(self):
        check = self.run_check(status_code=503)
        incident = Incident.objects.get()

        self.assertEqual(
            incident.status,
            Incident.Status.OPEN,
        )
        self.assertEqual(
            incident.monitor_id,
            self.monitor.pk,
        )
        self.assertEqual(
            incident.opening_check_id,
            check.pk,
        )
        self.assertIsNone(incident.recovery_check_id)
        self.assertIsNone(incident.resolved_at)

    def test_timeout_opens_incident(self):
        check = self.run_check(
            error=httpx.ReadTimeout("Test timeout")
        )
        incident = Incident.objects.get()

        self.assertEqual(
            incident.status,
            Incident.Status.OPEN,
        )
        self.assertEqual(
            incident.opening_check_id,
            check.pk,
        )

    def test_repeated_failure_keeps_same_incident(self):
        first_check = self.run_check(status_code=503)
        first_incident = Incident.objects.get()

        self.run_check(status_code=500)

        self.assertEqual(Incident.objects.count(), 1)

        incident = Incident.objects.get()

        self.assertEqual(
            incident.pk,
            first_incident.pk,
        )
        self.assertEqual(
            incident.opening_check_id,
            first_check.pk,
        )
        self.assertEqual(
            incident.status,
            Incident.Status.OPEN,
        )

    def test_recovery_resolves_open_incident(self):
        self.run_check(status_code=503)
        recovery = self.run_check(status_code=200)

        incident = Incident.objects.get()

        self.assertEqual(
            incident.status,
            Incident.Status.RESOLVED,
        )
        self.assertEqual(
            incident.recovery_check_id,
            recovery.pk,
        )
        self.assertIsNotNone(incident.resolved_at)

    def test_healthy_service_does_not_create_incident(self):
        self.run_check(status_code=200)

        self.assertFalse(Incident.objects.exists())

    def test_new_failure_after_recovery_opens_new_incident(self):
        self.run_check(status_code=503)
        first_incident = Incident.objects.get()

        self.run_check(status_code=200)
        new_failure = self.run_check(status_code=500)

        first_incident.refresh_from_db()

        self.assertEqual(
            first_incident.status,
            Incident.Status.RESOLVED,
        )
        self.assertEqual(Incident.objects.count(), 2)

        open_incident = Incident.objects.get(
            status=Incident.Status.OPEN
        )

        self.assertNotEqual(
            open_incident.pk,
            first_incident.pk,
        )
        self.assertEqual(
            open_incident.opening_check_id,
            new_failure.pk,
        )


class IncidentAccessTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="api-owner"
        )
        cls.other_user = User.objects.create_user(
            username="api-other"
        )

        application = Application.objects.create(
            name="Private API",
            slug="private-api",
            owner=cls.owner,
        )

        environment = Environment.objects.create(
            application=application,
            kind=Environment.Kind.DEVELOPMENT,
        )

        monitor = ServiceMonitor.objects.create(
            environment=environment,
            name="Private Health Check",
            url="https://example.com/health/",
        )

        check = MonitorCheck.objects.create(
            monitor=monitor,
            checked_url=monitor.url,
            expected_status_code=200,
            status=MonitorCheck.Status.DOWN,
            status_code=503,
            response_time_ms=25,
        )

        cls.incident = Incident.objects.create(
            monitor=monitor,
            title="Private service unavailable",
            opening_check=check,
        )

    def setUp(self):
        self.list_url = "/api/incidents/"
        self.detail_url = (
            f"/api/incidents/{self.incident.pk}/"
        )

    def test_anonymous_access_is_blocked(self):
        for url in (self.list_url, self.detail_url):
            with self.subTest(url=url):
                response = self.client.get(url)

                self.assertEqual(
                    response.status_code,
                    403,
                )

    def test_owner_can_list_and_open_incident(self):
        self.client.force_authenticate(user=self.owner)

        listing = self.client.get(self.list_url)
        detail = self.client.get(self.detail_url)

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            [item["id"] for item in listing.data],
            [self.incident.pk],
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            detail.data["id"],
            self.incident.pk,
        )

    def test_other_user_cannot_access_incident(self):
        self.client.force_authenticate(
            user=self.other_user
        )

        listing = self.client.get(self.list_url)
        detail = self.client.get(self.detail_url)

        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data, [])
        self.assertEqual(detail.status_code, 404)

    def test_api_does_not_allow_manual_changes(self):
        self.client.force_authenticate(user=self.owner)

        create = self.client.post(
            self.list_url,
            {},
            format="json",
        )
        update = self.client.patch(
            self.detail_url,
            {"status": "resolved"},
            format="json",
        )
        delete = self.client.delete(self.detail_url)

        self.assertEqual(create.status_code, 405)
        self.assertEqual(update.status_code, 405)
        self.assertEqual(delete.status_code, 405)

        self.incident.refresh_from_db()

        self.assertEqual(
            self.incident.status,
            Incident.Status.OPEN,
        )
        self.assertEqual(Incident.objects.count(), 1)