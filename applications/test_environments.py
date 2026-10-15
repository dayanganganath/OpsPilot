from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Application, Environment


class EnvironmentWriteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(username="env-owner")
        cls.other = User.objects.create_user(username="env-other")

        cls.application = Application.objects.create(
            name="Owner API",
            slug="owner-env-api",
            owner=cls.owner,
        )

        cls.second_application = Application.objects.create(
            name="Second Owner API",
            slug="second-owner-env-api",
            owner=cls.owner,
        )

        cls.other_application = Application.objects.create(
            name="Other API",
            slug="other-env-api",
            owner=cls.other,
        )

        cls.environment = Environment.objects.create(
            application=cls.application,
            kind=Environment.Kind.DEVELOPMENT,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.owner)
        self.list_url = "/api/environments/"
        self.detail_url = (
            f"/api/environments/{self.environment.pk}/"
        )

    def test_owner_can_create_environment(self):
        response = self.client.post(
            self.list_url,
            {
                "application": self.application.pk,
                "kind": "staging",
                "base_url": "https://staging.example.com",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        saved = Environment.objects.get(pk=response.data["id"])

        self.assertEqual(saved.application_id, self.application.pk)
        self.assertEqual(saved.kind, Environment.Kind.STAGING)
        self.assertEqual(
            saved.base_url,
            "https://staging.example.com",
        )

    def test_cannot_create_for_another_users_application(self):
        response = self.client.post(
            self.list_url,
            {
                "application": self.other_application.pk,
                "kind": "production",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("application", response.data)
        self.assertEqual(Environment.objects.count(), 1)

    def test_duplicate_environment_is_rejected(self):
        response = self.client.post(
            self.list_url,
            {
                "application": self.application.pk,
                "kind": "development",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.data)
        self.assertEqual(Environment.objects.count(), 1)

    def test_owner_can_update_environment(self):
        response = self.client.patch(
            self.detail_url,
            {
                "base_url": "https://dev.example.com",
                "is_active": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.environment.refresh_from_db()

        self.assertEqual(
            self.environment.base_url,
            "https://dev.example.com",
        )
        self.assertFalse(self.environment.is_active)
        self.assertEqual(
            self.environment.application_id,
            self.application.pk,
        )

    def test_other_user_cannot_update_environment(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            self.detail_url,
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.environment.refresh_from_db()
        self.assertTrue(self.environment.is_active)

    def test_existing_environment_cannot_change_application(self):
        response = self.client.patch(
            self.detail_url,
            {"application": self.second_application.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("application", response.data)

        self.environment.refresh_from_db()
        self.assertEqual(
            self.environment.application_id,
            self.application.pk,
        )

    def test_edit_cannot_create_duplicate_kind(self):
        staging = Environment.objects.create(
            application=self.application,
            kind=Environment.Kind.STAGING,
        )

        response = self.client.patch(
            f"/api/environments/{staging.pk}/",
            {"kind": "development"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        staging.refresh_from_db()
        self.assertEqual(staging.kind, Environment.Kind.STAGING)

    def test_invalid_base_url_is_rejected(self):
        response = self.client.patch(
            self.detail_url,
            {"base_url": "invalid-url"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("base_url", response.data)

        self.environment.refresh_from_db()
        self.assertEqual(self.environment.base_url, "")

    def test_anonymous_writes_are_blocked(self):
        self.client.force_authenticate(user=None)

        create = self.client.post(
            self.list_url,
            {
                "application": self.application.pk,
                "kind": "staging",
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
        self.assertEqual(Environment.objects.count(), 1)

        self.environment.refresh_from_db()
        self.assertTrue(self.environment.is_active)

    def test_delete_is_not_allowed(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            Environment.objects.filter(
                pk=self.environment.pk
            ).exists()
        )