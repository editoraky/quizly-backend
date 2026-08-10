"""HTTP views for the quiz API."""

import logging

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from quiz_app.models import Quiz
from quiz_app.api.exceptions import PipelineUnavailable, VideoUnavailable
from quiz_app.api.serializers import QuizSerializer, QuizCreateSerializer
from quiz_app.api.services import create_quiz_from_url

logger = logging.getLogger(__name__)

UNAVAILABLE = "Quiz generation is temporarily unavailable. Please try again later."


class QuizListView(generics.ListCreateAPIView):
    """List the user's quizzes or create a new one from a YouTube URL."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """Validate the URL, delegate creation, return the full quiz.

        The two domain errors are answered differently because they have
        different culprits. VideoUnavailable is caused by the submitted URL and
        repeats its message, so the caller can act on it. PipelineUnavailable is
        caused by the installation or an upstream service; its message can carry
        internal detail and therefore goes to the log while the client receives
        a neutral sentence. Anything else was never anticipated and stays a 500.
        """
        serializer = QuizCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            quiz = create_quiz_from_url(serializer.validated_data["url"], request.user)
        except VideoUnavailable as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        except PipelineUnavailable as error:
            logger.exception("Quiz generation failed: %s", error)
            return Response(
                {"detail": UNAVAILABLE}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        return Response(QuizSerializer(quiz).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        """Restrict the list to quizzes belonging to the current user."""
        return Quiz.objects.filter(owner=self.request.user)


class QuizDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Return, partially update or delete a quiz owned by the authenticated user."""

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        """Restrict lookups to quizzes belonging to the current user."""
        return Quiz.objects.filter(owner=self.request.user)
