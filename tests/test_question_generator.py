"""Unit tests for the Question Generator component (WP-04): FR-07, FR-08."""
from __future__ import annotations

import json

import pytest
from openai import APITimeoutError

from app.question_generator import generator


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content=None, raise_exc=None):
        self._content = content
        self._raise_exc = raise_exc
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if self._raise_exc:
            raise self._raise_exc
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, content=None, raise_exc=None):
        self.completions = _FakeCompletions(content, raise_exc)
        self.chat = _FakeChat(self.completions)


GOOD_PAYLOAD = json.dumps(
    {
        "questions": [
            {"text": "Tell me about a time you fixed a tricky bug.", "type": "behavioral"},
            {"text": "How would you index a slow SQL query?", "type": "technical"},
            {"text": "Describe a conflict with a teammate and how you resolved it.", "type": "behavioral"},
            {"text": "Explain how Flask routes a request to a view function.", "type": "technical"},
            {"text": "Tell me about a project you're proud of.", "type": "behavioral"},
        ]
    }
)


def test_generate_questions_returns_drafts_from_response():
    client = _FakeClient(content=GOOD_PAYLOAD)

    drafts = generator.generate_questions(
        "resume text", "job description text", ["Python", "Flask"], client=client
    )

    assert len(drafts) == 5
    assert drafts[0].order_index == 0
    assert {d.type for d in drafts} == {"behavioral", "technical"}
    assert client.completions.last_kwargs["response_format"] == {"type": "json_object"}


def test_generate_questions_requires_resume_text():
    with pytest.raises(generator.QuestionGenerationError, match="Resume text"):
        generator.generate_questions("", "job description", [], client=_FakeClient())


def test_generate_questions_requires_job_description():
    with pytest.raises(generator.QuestionGenerationError, match="job description"):
        generator.generate_questions("resume", "", [], client=_FakeClient())


def test_generate_questions_requires_configured_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(generator.QuestionGenerationError, match="not configured"):
        generator.generate_questions("resume", "job description", [])


def test_generate_questions_raises_on_api_failure():
    client = _FakeClient(raise_exc=APITimeoutError(request=None))

    with pytest.raises(generator.QuestionGenerationError, match="temporarily unavailable"):
        generator.generate_questions("resume", "job description", [], client=client)


def test_generate_questions_raises_on_malformed_json():
    client = _FakeClient(content="not json at all")

    with pytest.raises(generator.QuestionGenerationError, match="unusable response"):
        generator.generate_questions("resume", "job description", [], client=client)


def test_generate_questions_raises_when_too_few_usable_questions():
    payload = json.dumps({"questions": [{"text": "Only one question.", "type": "behavioral"}]})
    client = _FakeClient(content=payload)

    with pytest.raises(generator.QuestionGenerationError, match="Only 1 usable question"):
        generator.generate_questions("resume", "job description", [], client=client)


def test_generate_questions_skips_malformed_entries_but_keeps_good_ones():
    payload = json.dumps(
        {
            "questions": [
                {"text": "Good behavioral question one.", "type": "behavioral"},
                {"text": "", "type": "technical"},  # empty text, dropped
                {"text": "Bad type entry.", "type": "not-a-real-type"},  # bad type, dropped
                {"text": "Good technical question one.", "type": "technical"},
                {"text": "Good behavioral question two.", "type": "behavioral"},
                {"text": "Good technical question two.", "type": "technical"},
            ]
        }
    )
    client = _FakeClient(content=payload)

    drafts = generator.generate_questions(
        "resume", "job description", [], min_questions=4, client=client
    )

    assert len(drafts) == 4
    assert all(d.type in ("behavioral", "technical") for d in drafts)
