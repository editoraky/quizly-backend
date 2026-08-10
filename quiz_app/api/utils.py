"""Technical helpers for the quiz generation pipeline."""

import json
from pathlib import Path

import whisper
import yt_dlp
from django.conf import settings
from google import genai
from google.genai import types
from google.genai.errors import APIError
from yt_dlp.utils import YoutubeDLError

from quiz_app.api.exceptions import PipelineUnavailable, VideoUnavailable

GEMINI_MODEL = "gemini-3.6-flash"
WHISPER_MODEL = "base"
QUESTION_COUNT = 10


def download_options(target):
    """Return the yt-dlp settings that extract an mp3 audio track."""
    return {
        "format": "bestaudio/best",
        "outtmpl": str(target),
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
        ],
    }


def download_audio(url, target_dir):
    """Download the audio track of a YouTube video and return its path.

    YoutubeDLError is the base class of everything yt-dlp raises for a video it
    cannot fetch: deleted, private, region locked, no video at all. Translating
    it here keeps the library out of the view and turns a 500 into a 400.
    """
    target = Path(target_dir) / "audio"
    try:
        with yt_dlp.YoutubeDL(download_options(target)) as downloader:
            downloader.download([url])
    except YoutubeDLError as error:
        raise VideoUnavailable(
            "The video behind this URL could not be downloaded."
        ) from error
    return f"{target}.mp3"


def transcribe_audio(audio_path):
    """Turn an audio file into plain text using local Whisper.

    RuntimeError is what Whisper raises for audio it cannot read.
    FileNotFoundError is what Python raises when FFMPEG is missing from the
    PATH, because Whisper shells out to it. Neither is caused by the submitted
    URL, so both become PipelineUnavailable and end as 503 instead of 500.
    """
    try:
        model = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(audio_path)
    except (RuntimeError, FileNotFoundError) as error:
        raise PipelineUnavailable(
            "The audio track could not be transcribed."
        ) from error
    return result["text"]


def request_quiz(client, transcript):
    """Send the prompt to Gemini and return the raw response.

    response_mime_type asks the model for pure JSON, which spares the caller
    any cleanup of markdown fences. It shapes the format, not the structure.
    """
    return client.models.generate_content(
        model=GEMINI_MODEL,
        contents=build_prompt(transcript),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )


def generate_quiz_data(transcript):
    """Ask Gemini Flash for quiz data and return the parsed JSON payload.

    APIError covers everything the service itself reports: an invalid key, an
    exhausted quota, an outage. JSONDecodeError covers the case the format
    request cannot rule out — an answer that is not JSON after all. Both are
    ours to explain, never the caller's fault.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    try:
        response = request_quiz(client, transcript)
        return json.loads(response.text)
    except APIError as error:
        raise PipelineUnavailable("The quiz service is not available.") from error
    except json.JSONDecodeError as error:
        raise PipelineUnavailable(
            "The quiz service returned an unusable answer."
        ) from error


def build_prompt(transcript):
    """Build the instruction that forces a strict JSON quiz structure."""
    return (
        f"Create a quiz with exactly {QUESTION_COUNT} multiple-choice questions "
        "based on the transcript below. Answer in the language of the transcript. "
        "Return ONLY valid JSON with this exact structure: "
        '{"title": str, "description": str, "questions": [{"question_title": str, '
        '"question_options": [str, str, str, str], "answer": str}]}. '
        "The answer must be the exact text of one of the four options.\n\n"
        f"Transcript:\n{transcript}"
    )
