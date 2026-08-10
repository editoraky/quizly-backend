"""Shared test data for the quiz_app test package."""

FAKE_QUIZ_DATA = {
    "title": "Generated Quiz",
    "description": "A quiz about the video",
    "questions": [
        {
            "question_title": f"Question {number}",
            "question_options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": "Option A",
        }
        for number in range(1, 11)
    ],
}
