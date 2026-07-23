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


class QuizDetailView(generics.RetrieveUpdateAPIView):
    """Return or partially update a quiz owned by the authenticated user."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        """Restrict lookups to quizzes belonging to the current user."""
        return Quiz.objects.filter(owner=self.request.user)
