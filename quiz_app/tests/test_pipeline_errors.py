"""Tests for how the pipeline translates library errors into domain errors.

Every step of the pipeline can fail for reasons the user never sees: a video
that cannot be downloaded, a missing FFMPEG, an unreachable Gemini. Without a
translation each of those reaches the view as the library's own exception and
ends as a 500, no matter whose fault it was.
"""

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from google.genai.errors import APIError
from yt_dlp.utils import DownloadError

from quiz_app.api.exceptions import PipelineUnavailable, VideoUnavailable
from quiz_app.api.services import create_quiz_from_url
from quiz_app.models import Quiz
from quiz_app.tests.fixtures import FAKE_QUIZ_DATA
from quiz_app.api.utils import (
    download_audio,
    ensure_ffmpeg_available,
    generate_quiz_data,
    transcribe_audio,
)


class DownloadErrorTests(SimpleTestCase):
    """A failing download is caused by the submitted URL, not by the server."""

    def test_download_failure_becomes_video_unavailable(self):
        """yt-dlp errors are translated so the view can answer 400.

        DownloadError is the error yt-dlp raises for a video that is gone,
        private or region locked. It must not leave this module unchanged.
        """
        with patch("quiz_app.api.utils.yt_dlp.YoutubeDL") as downloader:
            session = downloader.return_value.__enter__.return_value
            session.download.side_effect = DownloadError("video unavailable")

            with self.assertRaises(VideoUnavailable):
                download_audio("https://www.youtube.com/watch?v=gone", "workdir")


class TranscriptionErrorTests(SimpleTestCase):
    """Whisper fails for reasons the caller cannot influence."""

    def test_unreadable_audio_becomes_pipeline_unavailable(self):
        """Whisper reports a file it cannot read as a plain RuntimeError."""
        with patch("quiz_app.api.utils.whisper.load_model") as load_model:
            transcribe = load_model.return_value.transcribe
            transcribe.side_effect = RuntimeError("Failed to load audio")

            with self.assertRaises(PipelineUnavailable):
                transcribe_audio("audio.mp3")

    def test_missing_ffmpeg_becomes_pipeline_unavailable(self):
        """Without FFMPEG on the PATH the conversion cannot even start.

        Whisper shells out to FFMPEG, so a missing binary surfaces as the
        FileNotFoundError of the subprocess call, not as a Whisper error.
        """
        with patch("quiz_app.api.utils.whisper.load_model") as load_model:
            transcribe = load_model.return_value.transcribe
            transcribe.side_effect = FileNotFoundError("ffmpeg")

            with self.assertRaises(PipelineUnavailable):
                transcribe_audio("audio.mp3")


class GenerationErrorTests(SimpleTestCase):
    """Gemini can refuse, be unreachable, or answer with something unusable."""

    def test_api_error_becomes_pipeline_unavailable(self):
        """An invalid key, an exhausted quota and an outage all raise APIError."""
        with patch("quiz_app.api.utils.genai.Client") as client:
            call = client.return_value.models.generate_content
            call.side_effect = APIError(503, {"error": {"message": "overloaded"}})

            with self.assertRaises(PipelineUnavailable):
                generate_quiz_data("transcript")

    def test_answer_that_is_not_json_becomes_pipeline_unavailable(self):
        """response_mime_type asks for JSON, but nothing guarantees it arrives."""
        with patch("quiz_app.api.utils.genai.Client") as client:
            call = client.return_value.models.generate_content
            call.return_value.text = "Sure! Here is your quiz:"

            with self.assertRaises(PipelineUnavailable):
                generate_quiz_data("transcript")


class MissingFfmpegTests(SimpleTestCase):
    """FFMPEG is a system requirement, not a Python package.

    yt-dlp reports a missing binary as a PostProcessingError, which belongs to
    the family it raises for videos it cannot fetch — the failure would read
    like a bad URL and answer 400. The check moves that decision to the front.
    """

    def test_missing_ffmpeg_is_reported_as_pipeline_unavailable(self):
        """which() returns None when the binary is nowhere on the PATH."""
        with patch("quiz_app.api.utils.shutil.which", return_value=None):
            with self.assertRaises(PipelineUnavailable):
                ensure_ffmpeg_available()

    def test_pipeline_stops_before_downloading_anything(self):
        """The check has to run first, otherwise it changes nothing.

        Running it after the download would let yt-dlp fail first and classify
        the missing binary as a problem with the video.
        """
        with patch("quiz_app.api.utils.shutil.which", return_value=None), \
             patch("quiz_app.api.services.download_audio") as download:

            with self.assertRaises(PipelineUnavailable):
                create_quiz_from_url("https://www.youtube.com/watch?v=any", None)

            download.assert_not_called()


class PipelineErrorResponseTests(APITestCase):
    """What the client sees when a step of the pipeline fails."""

    def setUp(self):
        """Log in, so the endpoint answers about the pipeline and not about auth."""
        User.objects.create_user(username="alice", password="SecurePass123")
        self.client.post(
            reverse("login"),
            {"username": "alice", "password": "SecurePass123"},
            format="json",
        )
        self.url = reverse("quiz-list")
        self.payload = {"url": "https://www.youtube.com/watch?v=example"}

    def test_unavailable_video_answers_400(self):
        """A video nobody can download is a problem with the submitted URL."""
        with patch(
            "quiz_app.api.views.create_quiz_from_url",
            side_effect=VideoUnavailable("The video could not be downloaded."),
        ):
            response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("could not be downloaded", str(response.data))

    def test_unavailable_pipeline_answers_503(self):
        """A broken step is our problem, so it must not be blamed on the input."""
        with patch(
            "quiz_app.api.views.create_quiz_from_url",
            side_effect=PipelineUnavailable("The quiz service is not available."),
        ):
            response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 503)

    def test_the_reason_goes_to_the_log_not_to_the_client(self):
        """503 answers stay neutral; the detail belongs in the operator's log.

        An exception message can carry internal information — a key, a host, a
        quota. The client gets a sentence it can act on, the log gets the rest.
        """
        with self.assertLogs("quiz_app.api.views", level="ERROR") as captured:
            with patch(
                "quiz_app.api.views.create_quiz_from_url",
                side_effect=PipelineUnavailable("invalid api key abc123"),
            ):
                response = self.client.post(self.url, self.payload, format="json")

        self.assertNotIn("abc123", str(response.data))
        self.assertIn("abc123", "\n".join(captured.output))

    def test_missing_ffmpeg_answers_503_through_the_endpoint(self):
        """The whole chain, from the check to the status code."""
        with patch("quiz_app.api.utils.shutil.which", return_value=None):
            response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 503)


class PartialSaveTests(TestCase):
    """A failure while saving must not leave a fragment behind."""

    def test_failure_while_saving_questions_leaves_no_quiz(self):
        """The quiz row is written first, the questions after it.

        Without the atomic block in _save_quiz a failure at the third question
        would leave a quiz with two questions in the database: visible in the
        list, unusable in the game.
        """
        user = User.objects.create_user(username="alice", password="SecurePass123")

        with patch("quiz_app.api.services.download_audio", return_value="a.mp3"), \
             patch("quiz_app.api.services.transcribe_audio", return_value="text"), \
             patch("quiz_app.api.services.generate_quiz_data", return_value=FAKE_QUIZ_DATA), \
             patch("quiz_app.api.services.ensure_ffmpeg_available"), \
             patch("quiz_app.api.services.Question.objects.create") as create_question:
            create_question.side_effect = [None, None, OSError("database is locked")]

            with self.assertRaises(OSError):
                create_quiz_from_url("https://www.youtube.com/watch?v=any", user)

        self.assertEqual(Quiz.objects.count(), 0)
