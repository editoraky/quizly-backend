"""Tests for the quiz_app serializers."""

from django.contrib.auth.models import User
from django.test import TestCase

from quiz_app.models import Question, Quiz


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
