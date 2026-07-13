"""Tests for the authentication endpoints."""

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


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
