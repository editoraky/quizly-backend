"""Business logic for quiz creation."""

import tempfile

from quiz_app.models import Quiz, Question
from quiz_app.api.utils import download_audio, transcribe_audio, generate_quiz_data


def create_quiz_from_url(url, user):
    """Create a quiz from a YouTube video via the AI pipeline."""
    with tempfile.TemporaryDirectory() as workdir:
        audio_path = download_audio(url, workdir)
        transcript = transcribe_audio(audio_path)
    quiz_data = generate_quiz_data(transcript)
    return _save_quiz(quiz_data, url, user)


def _save_quiz(quiz_data, url, user):
    """Persist the generated quiz and return it."""
    quiz = Quiz.objects.create(
        title=quiz_data["title"],
        description=quiz_data["description"],
        video_url=url,
        owner=user,
    )
    _save_questions(quiz_data["questions"], quiz)
    return quiz


def _save_questions(questions, quiz):
    """Persist all questions belonging to a quiz."""
    for question in questions:
        Question.objects.create(
            question_title=question["question_title"],
            question_options=question["question_options"],
            answer=question["answer"],
            quiz=quiz,
        )
