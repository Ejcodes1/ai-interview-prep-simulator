"""Regression test for the Render trailing-newline secret bug.

A value pasted into a hosting provider's dashboard with a trailing
newline (e.g. "sk-proj-...IfIA\\n") produces an invalid HTTP header when
used as a Bearer token — requests raises a clear ValueError, but httpx
(what the openai SDK uses internally) swallows the same failure and
re-raises it as a generic, unhelpful APIConnectionError. clean_env
strips whitespace so this can't happen regardless of how a secret was
pasted into whichever environment the app runs in.
"""
from __future__ import annotations

from app.env_utils import clean_env


def test_clean_env_strips_trailing_newline(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "sk-proj-abc123\n")

    assert clean_env("SOME_KEY") == "sk-proj-abc123"


def test_clean_env_strips_surrounding_whitespace(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "  sk-proj-abc123  \n")

    assert clean_env("SOME_KEY") == "sk-proj-abc123"


def test_clean_env_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)

    assert clean_env("SOME_KEY", "fallback") == "fallback"


def test_clean_env_returns_default_when_value_is_only_whitespace(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "   \n")

    assert clean_env("SOME_KEY", "fallback") == "fallback"


def test_clean_env_returns_none_default_when_unset_and_no_default(monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)

    assert clean_env("SOME_KEY") is None
