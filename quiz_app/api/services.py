"""Business logic for quiz creation."""

from quiz_app.models import Quiz, Question

PLACEHOLDER_QUESTION_COUNT = 10


def create_quiz_from_url(url, user):
    """Create a quiz owned by the user. Placeholder until the AI pipeline exists."""
    quiz = Quiz.objects.create(
        title="Generated Quiz",
        description="Placeholder quiz until the AI pipeline is wired in.",
        video_url=url,
        owner=user,
    )
    _create_placeholder_questions(quiz)
    return quiz


def _create_placeholder_questions(quiz):
    """Attach ten placeholder questions with four options each."""
    options = ["Option A", "Option B", "Option C", "Option D"]
    for number in range(1, PLACEHOLDER_QUESTION_COUNT + 1):
        Question.objects.create(
            question_title=f"Question {number}",
            question_options=options,
            answer=options[0],
            quiz=quiz,
        )
