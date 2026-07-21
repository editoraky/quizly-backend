"""Tests for the authentication endpoints."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


class RegistrationTests(APITestCase):
    """Verify how the register endpoint creates users and rejects bad input."""

    def setUp(self):
        """Provide the endpoint URL and a valid registration payload."""
        self.url = reverse("register")
        self.payload = {
            "username": "tester",
            "email": "tester@example.com",
            "password": "secret123",
            "confirmed_password": "secret123",
        }

    def test_registration_creates_a_user(self):
        """Valid data creates exactly one user and returns 201."""
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.first().username, "tester")

    def test_password_is_stored_as_a_hash(self):
        """The raw password never reaches the database."""
        self.client.post(self.url, self.payload, format="json")

        user = User.objects.get(username="tester")
        self.assertNotEqual(user.password, "secret123")
        self.assertTrue(user.check_password("secret123"))

    def test_mismatched_confirmation_is_rejected(self):
        """A confirmation that differs from the password creates no user."""
        self.payload["confirmed_password"] = "different123"

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_is_rejected(self):
        """An email that is already taken creates no second user."""
        User.objects.create_user(
            username="other",
            email="tester@example.com",
            password="secret123",
        )

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_username_is_rejected(self):
        """A username that is already taken creates no second user."""
        User.objects.create_user(
            username="tester",
            email="other@example.com",
            password="secret123",
        )

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)


class LoginTests(APITestCase):
    """Verify that login issues JWTs as HttpOnly cookies, not in the body."""

    def setUp(self):
        """Provide the endpoint URL and an already registered user."""
        self.url = reverse("login")
        self.user = User.objects.create_user(
            username="tester",
            email="tester@example.com",
            password="secret123",
        )
        self.credentials = {"username": "tester", "password": "secret123"}

    def test_login_returns_the_user_data(self):
        """Valid credentials return 200 and a user object."""
        response = self.client.post(self.url, self.credentials, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["user"]["id"], self.user.id)
        self.assertEqual(response.data["user"]["username"], "tester")
        self.assertEqual(response.data["user"]["email"], "tester@example.com")

    def test_login_sets_both_token_cookies(self):
        """Both tokens are handed over as cookies, not as body fields."""
        response = self.client.post(self.url, self.credentials, format="json")

        self.assertIn("access_token", response.cookies)
        self.assertIn("refresh_token", response.cookies)

    def test_token_cookies_are_httponly(self):
        """JavaScript must never be able to read the tokens."""
        response = self.client.post(self.url, self.credentials, format="json")

        self.assertTrue(response.cookies["access_token"]["httponly"])
        self.assertTrue(response.cookies["refresh_token"]["httponly"])

    def test_tokens_are_absent_from_the_response_body(self):
        """The body carries no token, so no script can pick one up."""
        response = self.client.post(self.url, self.credentials, format="json")

        self.assertNotIn("access", response.data)
        self.assertNotIn("refresh", response.data)

    def test_wrong_password_is_rejected(self):
        """Invalid credentials return 401 and set no cookies."""
        self.credentials["password"] = "wrong123"

        response = self.client.post(self.url, self.credentials, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access_token", response.cookies)
        self.assertNotIn("refresh_token", response.cookies)


class LogoutTests(APITestCase):
    """Testet den Logout-Endpoint: 200 + beide Auth-Cookies gelöscht."""

    def setUp(self):
        """Legt einen User an und loggt ihn ein, damit der Client die Cookies hält."""
        self.user = User.objects.create_user(
            username="tester", email="t@test.de", password="Passwort123"
        )
        self.client.post(reverse("login"), {"username": "tester", "password": "Passwort123"})

    def test_logout_returns_200_and_deletes_both_cookies(self):
        """Logout antwortet mit 200 und leert access_token und refresh_token."""
        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_logout_blacklists_the_refresh_token(self):
        """Nach dem Logout steht genau ein Refresh-Token auf der Blacklist."""
        self.assertEqual(BlacklistedToken.objects.count(), 0)

        self.client.post(reverse("logout"))

        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_logout_without_refresh_token_cookie_still_succeeds(self):
        """Logout ohne refresh_token-Cookie ist idempotent: 200 + beide Cookies geleert."""
        # Arrange: eingeloggt aus setUp, aber gezielt NUR den refresh_token entfernen
        del self.client.cookies["refresh_token"]

        # Act: eine Logout-Anfrage ohne refresh_token trifft ein
        response = self.client.post(reverse("logout"))

        # Assert: unser idempotenter Contract
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_logout_with_invalid_refresh_token_cookie_still_succeeds(self):
        """Logout mit ungültigem refresh_token-Cookie ist idempotent: 200 + beide Cookies geleert."""
        # Arrange: eingeloggt aus setUp, aber den refresh_token gezielt mit Müll überschreiben
        self.client.cookies["refresh_token"] = "this-is-not-a-valid-jwt"

        # Act: eine Logout-Anfrage mit ungültigem refresh_token trifft ein
        response = self.client.post(reverse("logout"))

        # Assert: identischer Idempotenz-Contract wie beim fehlenden Cookie
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_refresh_impossible_after_logout(self):
        """Beweist end-to-end: nach Logout ist der Refresh-Token geblacklistet → erneuter Refresh damit ergibt 401."""
        # den Token-WERT sichern, BEVOR der Logout das Cookie leert — danach käme man nicht mehr dran
        refresh_token = self.client.cookies["refresh_token"].value

        # ausloggen: blacklistet genau diesen Token und leert beide Cookies
        self.client.post(reverse("logout"))

        # den gesicherten (jetzt toten) Token erneut vorlegen
        self.client.cookies["refresh_token"] = refresh_token
        response = self.client.post(reverse("token_refresh"))

        self.assertEqual(response.status_code, 401)


class TokenRefreshTests(APITestCase):
    """Tests für POST /api/token/refresh/ — Access-Token aus dem refresh_token-Cookie erneuern."""

    def setUp(self):
        """User anlegen und über den echten Login-Endpoint einloggen → refresh_token-Cookie im Glas."""
        self.user = User.objects.create_user(username="quizuser", password="StrongPass123")
        self.client.post(
            reverse("login"),
            {"username": "quizuser", "password": "StrongPass123"},
        )

    def test_refresh_with_valid_cookie_returns_new_access_token(self):
        """Gültiges refresh_token-Cookie: 200 + detail + neues access_token-Cookie."""
        response = self.client.post(reverse("token_refresh"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], "Token refreshed")
        self.assertIn("access_token", response.cookies)

    def test_refresh_without_or_invalid_cookie_returns_401(self):
        """Kein oder ungültiges refresh_token-Cookie: 401 (Doku Seite 4)."""
        # Fall 1: gar kein refresh_token-Cookie
        self.client.cookies.pop("refresh_token", None)
        response = self.client.post(reverse("token_refresh"))
        self.assertEqual(response.status_code, 401)

        # Fall 2: refresh_token-Cookie vorhanden, aber Müll
        self.client.cookies["refresh_token"] = "this-is-not-a-valid-jwt"
        response = self.client.post(reverse("token_refresh"))
        self.assertEqual(response.status_code, 401)
