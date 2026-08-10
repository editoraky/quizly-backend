"""Business logic for quiz creation."""

import tempfile

from django.db import transaction

from quiz_app.models import Quiz, Question
from quiz_app.api.utils import (
    download_audio,
    ensure_ffmpeg_available,
    generate_quiz_data,
    transcribe_audio,
)


def create_quiz_from_url(url, user):
    """Create a quiz from a YouTube video via the AI pipeline.

    The FFMPEG check runs first on purpose: it costs a millisecond, while
    everything after it costs minutes and a download nobody needs if the
    conversion cannot happen anyway.
    """
    ensure_ffmpeg_available()
    with tempfile.TemporaryDirectory() as workdir:
        audio_path = download_audio(url, workdir)
        transcript = transcribe_audio(audio_path)
    quiz_data = generate_quiz_data(transcript)
    return _save_quiz(quiz_data, url, user)


def _save_quiz(quiz_data, url, user):
    """Persist the generated quiz and its questions as one unit.

    The quiz row is written before the questions, so a failure halfway through
    would leave a quiz with fewer than ten questions behind: visible in the
    list, unusable in the game. The atomic block makes it all or nothing.
    """
    with transaction.atomic():
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
