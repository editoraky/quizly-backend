"""Tests for how the pipeline translates library errors into domain errors.

Every step of the pipeline can fail for reasons the user never sees: a video
that cannot be downloaded, a missing FFMPEG, an unreachable Gemini. Without a
translation each of those reaches the view as the library's own exception and
ends as a 500, no matter whose fault it was.
"""

from unittest.mock import patch

from django.test import SimpleTestCase
from yt_dlp.utils import DownloadError

from quiz_app.api.exceptions import VideoUnavailable
from quiz_app.api.utils import download_audio


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
