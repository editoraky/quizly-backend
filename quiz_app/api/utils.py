"""Technical helpers for the quiz generation pipeline."""

import json
from pathlib import Path

import whisper
import yt_dlp
from django.conf import settings
from google import genai
from google.genai import types
from yt_dlp.utils import YoutubeDLError

from quiz_app.api.exceptions import VideoUnavailable

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
    """Turn an audio file into plain text using local Whisper."""
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(audio_path)
    return result["text"]


def generate_quiz_data(transcript):
    """Ask Gemini Flash for quiz data and return the parsed JSON payload."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=build_prompt(transcript),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


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
