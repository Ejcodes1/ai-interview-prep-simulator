"""Speech-to-Text Transcriber component — STUB (planned for WP-06).

Per the Component Diagram (Figure 5), the Web UI routes a recorded voice
answer (captured client-side via the MediaRecorder API, per Section 8) to
this component, which calls the Whisper API and feeds the resulting text
to the Answer Evaluator.

Covers: FR-10 (transcribe a recorded voice answer to text and show it to
the user before submission, per TR-02's mitigation — the user must be able
to confirm or edit the transcript).

Credentials: OPENAI_API_KEY, read from the environment via `app.config`
(see .env.example) — the Whisper API is part of the OpenAI API.

Not implemented yet — calling `transcribe_audio` raises NotImplementedError.
"""
from __future__ import annotations


class TranscriptionError(Exception):
    """Raised when the speech-to-text API call fails or audio is unusable."""


def transcribe_audio(audio_file) -> str:
    """Transcribe a recorded voice answer to text (FR-10).

    TODO(WP-06):
      - Accept the uploaded audio blob (e.g. audio/webm from MediaRecorder).
      - Validate the file (non-empty, supported format) and raise
        TranscriptionError with a user-facing message otherwise (FR-16).
      - Call the Whisper API and return the transcript text.
      - Let the caller (Web UI) display the transcript for user confirmation
        or edit before it is submitted as the Answer (TR-02 mitigation).
    """
    raise NotImplementedError(
        "Speech-to-text transcription is planned for WP-06. Use the typed "
        "text answer input (FR-09) for now."
    )
