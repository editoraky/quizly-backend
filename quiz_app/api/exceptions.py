"""Domain errors of the quiz generation pipeline.

They live in their own module on purpose: utils.py raises them and services.py
imports utils.py, so defining them in services.py would make the import
circular.

The split follows one question — whose fault is it? What the submitted URL
causes is the caller's problem and answers 400. What the installation or an
upstream service causes is ours and answers 503. Anything that reaches the view
as a plain Exception was never anticipated, and 500 is then the honest answer.
"""


class QuizGenerationError(Exception):
    """A quiz could not be generated. Base class for the two cases below."""


class VideoUnavailable(QuizGenerationError):
    """The video behind the submitted URL cannot be turned into a quiz.

    Deleted, private, region locked or simply not a video. Caused by the input,
    so the view answers 400 and repeats the message.
    """


class PipelineUnavailable(QuizGenerationError):
    """A step of the pipeline is not available or did not behave as expected.

    Missing FFMPEG, unreadable audio, an unreachable Gemini, an answer that is
    not the agreed JSON. None of it is caused by the input, so the view answers
    503 and keeps the details in the log instead of the response.
    """
