"""Speech-to-Text Transcriber component (Component Diagram, Figure 5) — WP-06.

See `transcriber.py` for FR-10.
"""
from .transcriber import TranscriptionError, transcribe_audio

__all__ = ["TranscriptionError", "transcribe_audio"]
