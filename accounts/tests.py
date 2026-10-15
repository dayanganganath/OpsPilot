from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class SessionAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.username = "login-test-user"
        cls.password = "OpsPilot-test-password-483!"

        get_user_model().objects.create_user(
            username=cls.username,
            password=cls.password,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def get_csrf(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        return response.json()["csrfToken"]

    def post_json(self, url, data):
        token = self.get_csrf()

        return self.client.post(
            url,
            data=data,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://127.0.0.1:5175",
        )

    def sign_in(self):
        return self.post_json(
            "/api/auth/login/",
            {
                "username": self.username,
                "password": self.password,
            },
        )

    def test_anonymous_session_returns_401(self):
        response = self.client.get("/api/auth/session/")

        self.assertEqual(response.status_code, 401)

    def test_valid_login_creates_session(self):
        response = self.sign_in()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["user"]["username"],
            self.username,
        )
        self.assertNotIn("password", response.json()["user"])

        session = self.client.get("/api/auth/session/")

        self.assertEqual(session.status_code, 200)
        self.assertEqual(
            session.json()["user"]["username"],
            self.username,
        )

    def test_wrong_password_is_rejected(self):
        response = self.post_json(
            "/api/auth/login/",
            {
                "username": self.username,
                "password": "wrong-password",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            self.client.get("/api/auth/session/").status_code,
            401,
        )

    def test_login_without_csrf_is_blocked(self):
        response = self.client.post(
            "/api/auth/login/",
            data={
                "username": self.username,
                "password": self.password,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.client.get("/api/auth/session/").status_code,
            401,
        )

    def test_login_from_untrusted_origin_is_blocked(self):
        token = self.get_csrf()

        response = self.client.post(
            "/api/auth/login/",
            data={
                "username": self.username,
                "password": self.password,
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://untrusted.example",
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_json_is_rejected(self):
        token = self.get_csrf()

        response = self.client.post(
            "/api/auth/login/",
            data="{invalid-json",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(response.status_code, 400)

    def test_logout_ends_session(self):
        self.assertEqual(self.sign_in().status_code, 200)

        # Login rotates the CSRF token, so fetch a fresh token.
        response = self.post_json("/api/auth/logout/", {})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get("/api/auth/session/").status_code,
            401,
        )

    def test_logout_without_csrf_is_blocked(self):
        self.assertEqual(self.sign_in().status_code, 200)

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.client.get("/api/auth/session/").status_code,
            200,
        )