# Quizly Backend

A Django REST API that turns YouTube videos into multiple-choice quizzes.
Audio is downloaded with yt-dlp, transcribed locally with Whisper AI and
sent to Google Gemini Flash, which generates 10 questions with 4 options each.

## Requirements

- Python 3.12 or newer
- **FFMPEG must be installed globally and available on your PATH.**
  Whisper AI cannot convert audio without it. Verify with `ffmpeg -version`.
  Windows: `winget install Gyan.FFmpeg` · macOS: `brew install ffmpeg` ·
  Linux: `sudo apt install ffmpeg`
- A free Gemini API key from https://aistudio.google.com/apikey

## Setup

```bash
git clone https://github.com/editoraky/quizly-backend.git
cd quizly-backend
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Create a file named `.env` in the project root:

```
GEMINI_API_KEY=your-key-here
```

Then run the migrations, create an admin account and start the server:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/`,
the admin panel at `http://127.0.0.1:8000/admin/`.

## Frontend

Serve the frontend from its own folder on port 5500:

```bash
python -m http.server 5500 --bind 127.0.0.1
```

Use `127.0.0.1`, not `localhost`. The browser treats them as different hosts,
which would stop the authentication cookies from being sent.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register/` | Create a new account |
| POST | `/api/login/` | Log in, sets both JWT cookies |
| POST | `/api/logout/` | Log out, blacklists the refresh token |
| POST | `/api/token/refresh/` | Issue a new access token |
| POST | `/api/quizzes/` | Create a quiz from a YouTube URL |
| GET | `/api/quizzes/` | List the current user's quizzes |
| GET | `/api/quizzes/{id}/` | Retrieve a single quiz |
| PATCH | `/api/quizzes/{id}/` | Update title and description |
| DELETE | `/api/quizzes/{id}/` | Delete a quiz and its questions |

Authentication uses JWT delivered as HttpOnly cookies. No `Authorization`
header is required or accepted. Quizzes are private: requesting a quiz owned
by another user returns 404.

## Tests

```bash
python manage.py test
```

## Notes

- On the first quiz generation Whisper downloads its model (~140 MB).
- Quiz generation takes roughly one to three minutes depending on video length.
