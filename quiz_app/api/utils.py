"""Technical helpers for the quiz generation pipeline."""

import json
from pathlib import Path

import whisper
import yt_dlp
from django.conf import settings
from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-2.5-flash"
WHISPER_MODEL = "base"
QUESTION_COUNT = 10


def download_audio(url, target_dir):
    """Download the audio track of a YouTube video and return its path."""
    target = Path(target_dir) / "audio"
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(target),
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
        ],
    }
    with yt_dlp.YoutubeDL(options) as downloader:
        downloader.download([url])
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
