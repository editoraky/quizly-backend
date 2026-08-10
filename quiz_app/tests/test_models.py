"""Tests for the quiz_app models."""

from django.contrib.auth.models import User
from django.test import TestCase

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
