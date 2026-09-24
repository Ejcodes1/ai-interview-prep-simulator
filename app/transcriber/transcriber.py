"""Speech-to-Text Transcriber component (WP-06).

Per the Component Diagram (Figure 5), the Web UI routes a recorded voice
answer (captured client-side via the MediaRecorder API, per Section 8) to
this component, which calls the Whisper API. The transcript is shown to
the candidate to confirm or edit before it is submitted as an Answer,
rather than being submitted automatically — that's the TR-02 mitigation
for inaccurate transcription of accented or low-quality audio.

Covers: FR-10 (transcribe a recorded voice answer to text and show it to
the user before submission).
"""
from __future__ import annotations

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "whisper-1"
DEFAULT_TIMEOUT_SECONDS = 15


class TranscriptionError(Exception):
    """Raised when the speech-to-text API call fails or audio is unusable."""


def _build_client(client: OpenAI | None, timeout: float) -> OpenAI:
    if client is not None:
        return client
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise TranscriptionError(
            "Voice transcription is not configured (missing OPENAI_API_KEY). "
            "Use the typed answer input instead."
        )
    return OpenAI(api_key=api_key, timeout=timeout)


def transcribe_audio(
    audio_file,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """Transcribe a recorded voice answer to text (FR-10)."""
    filename = getattr(audio_file, "filename", None)
    if audio_file is None or not filename:
        raise TranscriptionError("No audio was provided.")

    data = audio_file.read()
    if not data:
        raise TranscriptionError("The recorded audio is empty.")

    resolved_model = model or os.environ.get("WHISPER_MODEL", DEFAULT_MODEL)

    try:
        # Client construction is inside this block too: an incompatible
        # openai/httpx dependency pair, or any other environment issue,
        # must degrade to a clear message here rather than a raw 500.
        resolved_client = _build_client(client, timeout)
        response = resolved_client.audio.transcriptions.create(
            model=resolved_model,
            file=(filename, data),
            timeout=timeout,
        )
    except TranscriptionError:
        raise
    except Exception as exc:
        logger.error("Transcription failed: %s: %s", type(exc).__name__, exc)
        raise TranscriptionError(
            "The transcription service is temporarily unavailable. "
            "Please try again, or type your answer instead."
        ) from exc

    text = (getattr(response, "text", "") or "").strip()
    if not text:
        raise TranscriptionError("No speech could be transcribed from the recording.")

    return text
