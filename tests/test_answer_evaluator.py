"""Unit tests for the Answer Evaluator component (WP-06): FR-11, FR-12."""
from __future__ import annotations

import json

import pytest
from openai import APITimeoutError

from app.answer_evaluator import evaluator


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

    def create(self, **kwargs):
        if self._raise_exc:
            raise self._raise_exc
        return _FakeResponse(self._content)


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, content=None, raise_exc=None):
        self.chat = _FakeChat(_FakeCompletions(content, raise_exc))


GOOD_PAYLOAD = json.dumps(
    {
        "score": 82,
        "strengths": "Clear structure and a concrete example.",
        "weaknesses": "Could quantify the impact more.",
        "suggestions": "Add a specific metric, e.g. response time improvement.",
    }
)


def test_evaluate_answer_returns_parsed_result():
    client = _FakeClient(content=GOOD_PAYLOAD)

    result = evaluator.evaluate_answer("Tell me about a bug you fixed.", "I found and fixed a bug.", client=client)

    assert result.score == 82
    assert "metric" in result.suggestions


def test_evaluate_answer_requires_answer_text():
    with pytest.raises(evaluator.AnswerEvaluationError, match="answer is required"):
        evaluator.evaluate_answer("A question", "   ", client=_FakeClient())


def test_evaluate_answer_requires_configured_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(evaluator.AnswerEvaluationError, match="not configured"):
        evaluator.evaluate_answer("A question", "An answer")


def test_evaluate_answer_raises_on_api_failure():
    client = _FakeClient(raise_exc=APITimeoutError(request=None))

    with pytest.raises(evaluator.AnswerEvaluationError, match="temporarily unavailable"):
        evaluator.evaluate_answer("A question", "An answer", client=client)


def test_evaluate_answer_raises_on_malformed_json():
    client = _FakeClient(content="nope not json")

    with pytest.raises(evaluator.AnswerEvaluationError, match="unusable response"):
        evaluator.evaluate_answer("A question", "An answer", client=client)


def test_evaluate_answer_requires_a_suggestion():
    payload = json.dumps({"score": 50, "strengths": "ok", "weaknesses": "ok", "suggestions": ""})
    client = _FakeClient(content=payload)

    with pytest.raises(evaluator.AnswerEvaluationError, match="improvement suggestion"):
        evaluator.evaluate_answer("A question", "An answer", client=client)


def test_evaluate_answer_clamps_score_to_0_100():
    payload = json.dumps({"score": 150, "strengths": "", "weaknesses": "", "suggestions": "Be more concise."})
    client = _FakeClient(content=payload)

    result = evaluator.evaluate_answer("A question", "An answer", client=client)

    assert result.score == 100
