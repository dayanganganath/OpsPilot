from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Application, Environment


class ApplicationAccessTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(username="owner")
        cls.other_user = User.objects.create_user(username="other")

        cls.application = Application.objects.create(
            name="Private Demo API",
            slug="private-demo-api",
            owner=cls.owner,
        )

        cls.environment = Environment.objects.create(
            application=cls.application,
            kind=Environment.Kind.DEVELOPMENT,
        )

    def test_anonymous_access_is_blocked(self):
        for endpoint in ("applications", "environments"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"/api/{endpoint}/")
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_owner_can_list_own_records(self):
        self.client.force_authenticate(user=self.owner)

        records = {
            "applications": self.application,
            "environments": self.environment,
        }

        for endpoint, record in records.items():
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"/api/{endpoint}/")

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    [item["id"] for item in response.data],
                    [record.pk],
                )

    def test_other_user_cannot_list_private_records(self):
        self.client.force_authenticate(user=self.other_user)

        for endpoint in ("applications", "environments"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"/api/{endpoint}/")

                self.assertEqual(
                    response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(response.data, [])

    def test_other_user_cannot_open_private_record_by_id(self):
        self.client.force_authenticate(user=self.other_user)

        records = {
            "applications": self.application,
            "environments": self.environment,
        }

        for endpoint, record in records.items():
            with self.subTest(endpoint=endpoint):
                response = self.client.get(
                    f"/api/{endpoint}/{record.pk}/"
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_404_NOT_FOUND,
                )