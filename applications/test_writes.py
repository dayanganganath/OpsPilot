from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Application


class ApplicationWriteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="write-owner"
        )
        cls.other = User.objects.create_user(
            username="write-other"
        )

        cls.application = Application.objects.create(
            name="Existing API",
            slug="existing-api",
            owner=cls.owner,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.owner)
        self.list_url = "/api/applications/"
        self.detail_url = (
            f"/api/applications/{self.application.pk}/"
        )

    def test_create_assigns_logged_in_owner(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "New API",
                "slug": "new-api",
                "description": "New service",
                "repository_url": "https://github.com/example/api",
                "owner": self.other.pk,
                "owner_username": self.other.username,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        saved = Application.objects.get(pk=response.data["id"])

        self.assertEqual(saved.name, "New API")
        self.assertEqual(saved.owner_id, self.owner.pk)
        self.assertEqual(
            response.data["owner_username"],
            self.owner.username,
        )

    def test_owner_can_update_without_transferring_ownership(self):
        response = self.client.patch(
            self.detail_url,
            {
                "name": "Updated API",
                "description": "Updated description",
                "is_active": False,
                "owner": self.other.pk,
                "owner_username": self.other.username,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.application.refresh_from_db()

        self.assertEqual(self.application.name, "Updated API")
        self.assertEqual(
            self.application.description,
            "Updated description",
        )
        self.assertFalse(self.application.is_active)
        self.assertEqual(
            self.application.owner_id,
            self.owner.pk,
        )

    def test_other_user_cannot_update_application(self):
        self.client.force_authenticate(user=self.other)

        response = self.client.patch(
            self.detail_url,
            {"name": "Unauthorized change"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

        self.application.refresh_from_db()

        self.assertEqual(self.application.name, "Existing API")
        self.assertEqual(
            self.application.owner_id,
            self.owner.pk,
        )

    def test_anonymous_user_cannot_create_application(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.list_url,
            {"name": "New API", "slug": "new-api"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Application.objects.count(), 1)

    def test_short_name_is_rejected(self):
        response = self.client.post(
            self.list_url,
            {"name": " X ", "slug": "short-name"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data)
        self.assertEqual(Application.objects.count(), 1)

    def test_duplicate_slug_is_rejected(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Duplicate API",
                "slug": self.application.slug,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("slug", response.data)
        self.assertEqual(Application.objects.count(), 1)

    def test_invalid_repository_url_is_rejected(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Invalid URL API",
                "slug": "invalid-url-api",
                "repository_url": "not-a-url",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("repository_url", response.data)
        self.assertEqual(Application.objects.count(), 1)

    def test_delete_is_not_allowed(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            Application.objects.filter(
                pk=self.application.pk
            ).exists()
        )