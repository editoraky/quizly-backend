"""HTTP views for the quiz API."""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from quiz_app.models import Quiz
from quiz_app.api.serializers import QuizSerializer


class QuizListView(generics.ListAPIView):
    """Return the quizzes owned by the authenticated user."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Restrict the list to quizzes belonging to the current user."""
        return Quiz.objects.filter(owner=self.request.user)
