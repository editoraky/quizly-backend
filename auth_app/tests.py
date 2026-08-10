"""Tests for the authentication endpoints."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken


class RegistrationTests(APITestCase):
    """Verify how the register endpoint creates users and rejects bad input."""

    def setUp(self):
        """Provide the endpoint URL and a valid registration payload."""
        self.url = reverse("register")
        self.payload = {
            "username": "tester",
            "email": "tester@example.com",
            "password": "SecurePass123",
            "confirmed_password": "SecurePass123",
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
        self.assertNotEqual(user.password, "SecurePass123")
        self.assertTrue(user.check_password("SecurePass123"))

    def test_mismatched_confirmation_is_rejected(self):
        """A confirmation that differs from the password creates no user."""
        self.payload["confirmed_password"] = "different123"

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_weak_password_is_rejected(self):
        """AUTH_PASSWORD_VALIDATORS apply to registration, not only to the shell.

        Django runs them only where they are called, so this test is the proof
        that the endpoint calls them. Each password fails a different validator:
        too short, too common, entirely numeric.
        """
        for weak in ["abc", "password", "12345678"]:
            with self.subTest(password=weak):
                self.payload["password"] = weak
                self.payload["confirmed_password"] = weak

                response = self.client.post(self.url, self.payload, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("password", response.data)
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
    """Test the logout endpoint: 200 + both auth cookies deleted."""

    def setUp(self):
        """Create a user and log them in so the client holds the cookies."""
        self.user = User.objects.create_user(
            username="tester", email="t@test.de", password="Passwort123"
        )
        self.client.post(reverse("login"), {"username": "tester", "password": "Passwort123"})

    def test_logout_returns_200_and_deletes_both_cookies(self):
        """Logout answers 200 and clears access_token and refresh_token."""
        response = self.client.post(reverse("logout"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_logout_blacklists_the_refresh_token(self):
        """After logout exactly one refresh token is on the blacklist."""
        self.assertEqual(BlacklistedToken.objects.count(), 0)

        self.client.post(reverse("logout"))

        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_logout_without_refresh_token_cookie_still_succeeds(self):
        """Logout without a refresh_token cookie is idempotent: 200 + both cookies cleared."""
        # Arrange: logged in from setUp, but deliberately remove ONLY the refresh_token
        del self.client.cookies["refresh_token"]

        # Act: a logout request without a refresh_token arrives
        response = self.client.post(reverse("logout"))

        # Assert: our idempotent contract
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_logout_with_invalid_refresh_token_cookie_still_succeeds(self):
        """Logout with an invalid refresh_token cookie is idempotent: 200 + both cookies cleared."""
        # Arrange: logged in from setUp, but deliberately overwrite the refresh_token with garbage
        self.client.cookies["refresh_token"] = "this-is-not-a-valid-jwt"

        # Act: a logout request with an invalid refresh_token arrives
        response = self.client.post(reverse("logout"))

        # Assert: identical idempotency contract as with the missing cookie
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["access_token"].value, "")
        self.assertEqual(response.cookies["refresh_token"].value, "")

    def test_refresh_impossible_after_logout(self):
        """Prove end-to-end: after logout the refresh token is blacklisted → refreshing with it again yields 401."""
        # save the token VALUE BEFORE logout clears the cookie — afterwards it would be unreachable
        refresh_token = self.client.cookies["refresh_token"].value

        # log out: blacklists exactly this token and clears both cookies
        self.client.post(reverse("logout"))

        # present the saved (now dead) token again
        self.client.cookies["refresh_token"] = refresh_token
        response = self.client.post(reverse("token_refresh"))

        self.assertEqual(response.status_code, 401)

    def test_logout_requires_authentication(self):
        """Without a valid access_token cookie logout is protected: 401 (Docs page 3)."""
        fresh_client = APIClient()  # never logged in → no access_token cookie
        response = fresh_client.post(reverse("logout"))
        self.assertEqual(response.status_code, 401)


class TokenRefreshTests(APITestCase):
    """Tests for POST /api/token/refresh/ — refresh the access token from the refresh_token cookie."""

    def setUp(self):
        """Create a user and log in via the real login endpoint → refresh_token cookie in the jar."""
        self.user = User.objects.create_user(username="quizuser", password="StrongPass123")
        self.client.post(
            reverse("login"),
            {"username": "quizuser", "password": "StrongPass123"},
        )

    def test_refresh_with_valid_cookie_returns_new_access_token(self):
        """Valid refresh_token cookie: 200 + detail + new access_token cookie."""
        response = self.client.post(reverse("token_refresh"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], "Token refreshed")
        self.assertIn("access_token", response.cookies)

    def test_refresh_without_or_invalid_cookie_returns_401(self):
        """Missing or invalid refresh_token cookie: 401 (Docs page 4)."""
        # Case 1: no refresh_token cookie at all
        self.client.cookies.pop("refresh_token", None)
        response = self.client.post(reverse("token_refresh"))
        self.assertEqual(response.status_code, 401)

        # Case 2: refresh_token cookie present, but garbage
        self.client.cookies["refresh_token"] = "this-is-not-a-valid-jwt"
        response = self.client.post(reverse("token_refresh"))
        self.assertEqual(response.status_code, 401)
