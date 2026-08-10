"""Tests for the quiz endpoints: listing, detail, creation."""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from quiz_app.models import Quiz
from quiz_app.tests.fixtures import FAKE_QUIZ_DATA


class QuizListTests(APITestCase):
    """Verify GET /api/quizzes/ returns only the authenticated user's quizzes."""

    def setUp(self):
        """Create two users with one quiz each."""
        self.user = User.objects.create_user(username="alice", password="secret123")
        self.other = User.objects.create_user(username="bob", password="secret123")
        Quiz.objects.create(
            title="Alice Quiz",
            description="Quiz Description",
            video_url="https://www.youtube.com/watch?v=alice",
            owner=self.user,
        )
        Quiz.objects.create(
            title="Bob Quiz",
            description="Quiz Description",
            video_url="https://www.youtube.com/watch?v=bob",
            owner=self.other,
        )
        self.url = reverse("quiz-list")

    def test_list_requires_authentication(self):
        """Without an access token cookie the endpoint must answer 401."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    def test_list_returns_only_own_quizzes(self):
        """A logged-in user sees exactly one quiz: their own."""
        self.client.post(
            reverse("login"),
            {"username": "alice", "password": "secret123"},
            format="json",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Alice Quiz")


class QuizDetailTests(APITestCase):
    """Verify GET /api/quizzes/{id}/ enforces ownership."""

    def setUp(self):
        """Create two users with one quiz each."""
        self.user = User.objects.create_user(username="alice", password="secret123")
        self.other = User.objects.create_user(username="bob", password="secret123")
        self.own_quiz = Quiz.objects.create(
            title="Alice Quiz",
            description="Quiz Description",
            video_url="https://www.youtube.com/watch?v=alice",
            owner=self.user,
        )
        self.foreign_quiz = Quiz.objects.create(
            title="Bob Quiz",
            description="Quiz Description",
            video_url="https://www.youtube.com/watch?v=bob",
            owner=self.other,
        )

    def login(self):
        """Log in as alice so the client holds the access token cookie."""
        self.client.post(
            reverse("login"),
            {"username": "alice", "password": "secret123"},
            format="json",
        )

    def test_detail_requires_authentication(self):
        """Without an access token cookie the endpoint must answer 401."""
        url = reverse("quiz-detail", args=[self.own_quiz.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 401)

    def test_owner_can_retrieve_own_quiz(self):
        """The owner receives their quiz with 200."""
        self.login()
        url = reverse("quiz-detail", args=[self.own_quiz.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Alice Quiz")

    def test_foreign_quiz_returns_404(self):
        """A quiz owned by someone else must be invisible, not forbidden."""
        self.login()
        url = reverse("quiz-detail", args=[self.foreign_quiz.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_patch_requires_authentication(self):
        """Without an access token cookie the endpoint must answer 401."""
        url = reverse("quiz-detail", args=[self.own_quiz.id])

        response = self.client.patch(url, {"title": "New"}, format="json")

        self.assertEqual(response.status_code, 401)

    def test_owner_can_patch_title_and_description(self):
        """The owner may update title and description."""
        self.login()
        url = reverse("quiz-detail", args=[self.own_quiz.id])

        response = self.client.patch(
            url,
            {"title": "Updated Title", "description": "Updated Description"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.own_quiz.refresh_from_db()
        self.assertEqual(self.own_quiz.title, "Updated Title")
        self.assertEqual(self.own_quiz.description, "Updated Description")

    def test_patch_ignores_read_only_fields(self):
        """video_url must stay unchanged even if the client sends it."""
        self.login()
        url = reverse("quiz-detail", args=[self.own_quiz.id])

        response = self.client.patch(
            url,
            {
                "title": "Updated Title",
                "video_url": "https://www.youtube.com/watch?v=hacked",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.own_quiz.refresh_from_db()
        self.assertEqual(
            self.own_quiz.video_url,
            "https://www.youtube.com/watch?v=alice",
        )

    def test_patch_foreign_quiz_returns_404(self):
        """Patching someone else's quiz must answer 404."""
        self.login()
        url = reverse("quiz-detail", args=[self.foreign_quiz.id])

        response = self.client.patch(url, {"title": "Hacked"}, format="json")

        self.assertEqual(response.status_code, 404)

    def test_delete_requires_authentication(self):
        """Without an access token cookie the endpoint must answer 401."""
        url = reverse("quiz-detail", args=[self.own_quiz.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 401)

    def test_owner_can_delete_own_quiz(self):
        """Deleting an own quiz answers 204 and removes it from the database."""
        self.login()
        url = reverse("quiz-detail", args=[self.own_quiz.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Quiz.objects.filter(id=self.own_quiz.id).exists())

    def test_delete_foreign_quiz_returns_404(self):
        """Deleting someone else's quiz answers 404 and keeps it intact."""
        self.login()
        url = reverse("quiz-detail", args=[self.foreign_quiz.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Quiz.objects.filter(id=self.foreign_quiz.id).exists())


class QuizCreateTests(APITestCase):
    """Verify POST /api/quizzes/ creates a quiz from a YouTube URL."""

    def setUp(self):
        """Create a user and log in so the client holds the token cookie."""
        self.user = User.objects.create_user(username="alice", password="secret123")
        self.url = reverse("quiz-list")
        self.payload = {"url": "https://www.youtube.com/watch?v=example"}

    def login(self):
        """Log in as alice."""
        self.client.post(
            reverse("login"),
            {"username": "alice", "password": "secret123"},
            format="json",
        )

    def test_create_requires_authentication(self):
        """Without an access token cookie the endpoint must answer 401."""
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 401)

    def test_create_returns_201_with_full_quiz(self):
        """The response carries the full quiz, owned by the current user."""
        self.login()

        with patch("quiz_app.api.services.download_audio", return_value="a.mp3"), \
             patch("quiz_app.api.services.transcribe_audio", return_value="transcript"), \
             patch("quiz_app.api.services.generate_quiz_data", return_value=FAKE_QUIZ_DATA):
            response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["video_url"], self.payload["url"])
        self.assertEqual(len(response.data["questions"]), 10)
        self.assertEqual(Quiz.objects.get(id=response.data["id"]).owner, self.user)

    def test_create_rejects_invalid_url(self):
        """A malformed URL must answer 400."""
        self.login()

        response = self.client.post(self.url, {"url": "not-a-url"}, format="json")

        self.assertEqual(response.status_code, 400)
