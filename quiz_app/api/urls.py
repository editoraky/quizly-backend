"""URL routes for the quiz API."""

from django.urls import path

from quiz_app.api.views import QuizListView

urlpatterns = [
    path("quizzes/", QuizListView.as_view(), name="quiz-list"),
]
