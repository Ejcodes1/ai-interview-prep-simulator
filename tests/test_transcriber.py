"""Unit tests for the Speech-to-Text Transcriber component (WP-06): FR-10."""
from __future__ import annotations

import io

import pytest
from openai import APITimeoutError
from werkzeug.datastructures import FileStorage

from app.transcriber import transcriber


class _FakeTranscript:
    def __init__(self, text):
        self.text = text


class _FakeTranscriptions:
    def __init__(self, text=None, raise_exc=None):
        self._text = text
        self._raise_exc = raise_exc

    def create(self, **kwargs):
        if self._raise_exc:
            raise self._raise_exc
        return _FakeTranscript(self._text)


class _FakeAudio:
    def __init__(self, transcriptions):
        self.transcriptions = transcriptions


class _FakeClient:
    def __init__(self, text=None, raise_exc=None):
        self.audio = _FakeAudio(_FakeTranscriptions(text, raise_exc))


def _audio_file(data=b"fake-audio-bytes", filename="answer.webm"):
    return FileStorage(stream=io.BytesIO(data), filename=filename)


def test_transcribe_audio_returns_stripped_text():
    client = _FakeClient(text="  I fixed a bug in the API.  ")

    text = transcriber.transcribe_audio(_audio_file(), client=client)

    assert text == "I fixed a bug in the API."


def test_transcribe_audio_requires_a_file():
    with pytest.raises(transcriber.TranscriptionError, match="No audio"):
        transcriber.transcribe_audio(_audio_file(filename=""), client=_FakeClient())


def test_transcribe_audio_requires_configured_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(transcriber.TranscriptionError, match="not configured"):
        transcriber.transcribe_audio(_audio_file())


def test_transcribe_audio_raises_on_api_failure():
    client = _FakeClient(raise_exc=APITimeoutError(request=None))

    with pytest.raises(transcriber.TranscriptionError, match="temporarily unavailable"):
        transcriber.transcribe_audio(_audio_file(), client=client)


def test_transcribe_audio_raises_when_no_speech_detected():
    client = _FakeClient(text="")

    with pytest.raises(transcriber.TranscriptionError, match="No speech could be transcribed"):
        transcriber.transcribe_audio(_audio_file(), client=client)
