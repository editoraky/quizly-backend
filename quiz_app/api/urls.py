"""URL routes for the quiz API."""

from django.urls import path

from quiz_app.api.views import QuizListView, QuizDetailView

urlpatterns = [
    path("quizzes/", QuizListView.as_view(), name="quiz-list"),
    path("quizzes/<int:pk>/", QuizDetailView.as_view(), name="quiz-detail"),
]
