"""Database models for quizzes and their questions."""

from django.contrib.auth.models import User
from django.db import models


class Quiz(models.Model):
    """A quiz generated from a YouTube video, owned by a single user."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    video_url = models.URLField()
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "quizzes"
        ordering = ["-created_at"]

    def __str__(self):
        """Show the title in the admin panel and in shell output."""
        return self.title


class Question(models.Model):
    """A single question with four options, belonging to one quiz."""

    question_title = models.TextField()
    question_options = models.JSONField()
    answer = models.CharField(max_length=255)
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        """Show the question text in the admin panel."""
        return self.question_title
