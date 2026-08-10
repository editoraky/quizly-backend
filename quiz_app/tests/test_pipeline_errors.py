"""Tests for how the pipeline translates library errors into domain errors.

Every step of the pipeline can fail for reasons the user never sees: a video
that cannot be downloaded, a missing FFMPEG, an unreachable Gemini. Without a
translation each of those reaches the view as the library's own exception and
ends as a 500, no matter whose fault it was.
"""

from unittest.mock import patch

from django.test import SimpleTestCase
from google.genai.errors import APIError
from yt_dlp.utils import DownloadError

from quiz_app.api.exceptions import PipelineUnavailable, VideoUnavailable
from quiz_app.api.utils import download_audio, generate_quiz_data, transcribe_audio


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
