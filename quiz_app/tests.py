"""Tests for the quiz_app models."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from quiz_app.models import Question, Quiz


class QuizModelTests(TestCase):
    """Verify how a Quiz relates to the user who owns it."""

    def setUp(self):
        """Provide a user that acts as the quiz owner."""
        self.user = User.objects.create_user(
            username="tester",
            password="secret123",
        )

    def test_quiz_is_linked_to_its_owner(self):
        """A quiz stores its owner and is reachable via the reverse relation."""
        quiz = Quiz.objects.create(
            title="Photosynthesis",
            description="How plants convert light into energy.",
            video_url="https://www.youtube.com/watch?v=abc123",
            owner=self.user,
        )
        self.assertEqual(quiz.owner, self.user)
        self.assertIn(quiz, self.user.quizzes.all())

    def test_quizzes_are_deleted_with_their_owner(self):
        """Deleting a user removes the quizzes that belong to them."""
        Quiz.objects.create(
            title="Photosynthesis",
            description="How plants convert light into energy.",
            video_url="https://www.youtube.com/watch?v=abc123",
            owner=self.user,
        )
        self.user.delete()
        self.assertEqual(Quiz.objects.count(), 0)


class QuestionModelTests(TestCase):
    """Verify how a Question relates to the quiz it belongs to."""

    def setUp(self):
        """Provide a user and a quiz to attach questions to."""
        self.user = User.objects.create_user(
            username="tester",
            password="secret123",
        )
        self.quiz = Quiz.objects.create(
            title="Photosynthesis",
            description="How plants convert light into energy.",
            video_url="https://www.youtube.com/watch?v=abc123",
            owner=self.user,
        )

    def test_question_is_linked_to_its_quiz(self):
        """A question stores its quiz and is reachable via the reverse relation."""
        question = Question.objects.create(
            question_title="What do plants absorb?",
            question_options=["Sunlight", "Moonlight", "Sound", "Wind"],
            answer="Sunlight",
            quiz=self.quiz,
        )
        self.assertEqual(question.quiz, self.quiz)
        self.assertIn(question, self.quiz.questions.all())

    def test_questions_are_deleted_with_their_quiz(self):
        """Deleting a quiz removes the questions that belong to it."""
        Question.objects.create(
            question_title="What do plants absorb?",
            question_options=["Sunlight", "Moonlight", "Sound", "Wind"],
            answer="Sunlight",
            quiz=self.quiz,
        )
        self.quiz.delete()
        self.assertEqual(Question.objects.count(), 0)

    def test_question_options_survive_as_a_list(self):
        """Options are stored as JSON and come back as a real Python list."""
        Question.objects.create(
            question_title="What do plants absorb?",
            question_options=["Sunlight", "Moonlight", "Sound", "Wind"],
            answer="Sunlight",
            quiz=self.quiz,
        )
        reloaded = Question.objects.get(question_title="What do plants absorb?")
        self.assertIsInstance(reloaded.question_options, list)
        self.assertEqual(len(reloaded.question_options), 4)
        self.assertIn(reloaded.answer, reloaded.question_options)


class QuizSerializerTests(TestCase):
    """Verify the QuizSerializer output shape matches the documented contract."""

    def setUp(self):
        """Create one user and one owned quiz (no questions needed)."""
        self.user = User.objects.create_user(
            username="alice",
            password="secret123",
        )
        self.quiz = Quiz.objects.create(
            title="Quiz Title",
            description="Quiz Description",
            video_url="https://www.youtube.com/watch?v=example",
            owner=self.user,
        )

    def test_serializer_exposes_exactly_the_contract_fields(self):
        """Output must carry the seven documented quiz fields, nothing else."""
        from quiz_app.api.serializers import QuizSerializer

        data = QuizSerializer(self.quiz).data

        expected = {
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        }
        self.assertEqual(set(data.keys()), expected)

    def test_questions_are_nested_objects_with_full_data(self):
        """Each question must be a nested object with options and answer."""
        from quiz_app.api.serializers import QuizSerializer

        Question.objects.create(
            question_title="Question 1",
            question_options=["Option A", "Option B", "Option C", "Option D"],
            answer="Option A",
            quiz=self.quiz,
        )

        question = QuizSerializer(self.quiz).data["questions"][0]

        expected = {
            "id",
            "question_title",
            "question_options",
            "answer",
            "created_at",
            "updated_at",
        }
        self.assertEqual(set(question.keys()), expected)
        self.assertEqual(
            question["question_options"],
            ["Option A", "Option B", "Option C", "Option D"],
        )
        self.assertEqual(question["answer"], "Option A")


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

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["video_url"], self.payload["url"])
        self.assertTrue(len(response.data["questions"]) > 0)
        self.assertEqual(Quiz.objects.get(id=response.data["id"]).owner, self.user)

    def test_create_rejects_invalid_url(self):
        """A malformed URL must answer 400."""
        self.login()

        response = self.client.post(self.url, {"url": "not-a-url"}, format="json")

        self.assertEqual(response.status_code, 400)
