"""Serializers for the quiz API."""

from rest_framework import serializers

from quiz_app.models import Quiz, Question


class QuestionSerializer(serializers.ModelSerializer):
    """Serialize a single question with its options and answer."""

    class Meta:
        model = Question
        fields = [
            "id",
            "question_title",
            "question_options",
            "answer",
            "created_at",
            "updated_at",
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Serialize a quiz for the documented API contract."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "updated_at",
            "video_url",
            "questions",
        ]

        read_only_fields = [
            "video_url",
            "created_at",
            "updated_at"
        ]
