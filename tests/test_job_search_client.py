"""Unit tests for the Job Search Module (WP-03): FR-02, FR-03, TR-03."""
from __future__ import annotations

import requests

from app.job_search import client


class FakeResponse:
    def __init__(self, json_data=None, raise_exc: Exception | None = None):
        self._json_data = json_data or {}
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._json_data


ADZUNA_PAYLOAD = {
    "results": [
        {
            "title": "Backend Software Engineer",
            "company": {"display_name": "Acme Corp"},
            "description": "Build APIs " * 40,  # long enough to force truncation
        },
        {
            "title": "  Data Engineer  ",
            "company": {"display_name": "Widgets Inc"},
            "description": "Work with pipelines &amp; ETL.",
        },
    ]
}


def test_search_job_postings_returns_mapped_results(monkeypatch):
    monkeypatch.setattr(
        client.requests, "get", lambda *a, **k: FakeResponse(ADZUNA_PAYLOAD)
    )

    response = client.search_job_postings(
        "engineer", app_id="id", app_key="key", cache={}
    )

    assert response.from_cache is False
    assert len(response.results) == 2
    assert response.results[0].title == "Backend Software Engineer"
    assert response.results[0].company == "Acme Corp"
    assert response.results[1].title == "Data Engineer"  # stripped
    assert "&amp;" not in response.results[1].description  # unescaped


def test_search_job_postings_summary_is_truncated(monkeypatch):
    monkeypatch.setattr(
        client.requests, "get", lambda *a, **k: FakeResponse(ADZUNA_PAYLOAD)
    )

    response = client.search_job_postings("engineer", app_id="id", app_key="key")

    long_result = response.results[0]
    assert len(long_result.summary) <= client.SUMMARY_MAX_LENGTH + 1
    assert long_result.summary.endswith("…")
    assert len(long_result.description) > len(long_result.summary)


def test_search_job_postings_populates_cache(monkeypatch):
    monkeypatch.setattr(
        client.requests, "get", lambda *a, **k: FakeResponse(ADZUNA_PAYLOAD)
    )
    cache: dict = {}

    client.search_job_postings("engineer", app_id="id", app_key="key", cache=cache)

    assert client.CACHE_KEY in cache
    assert cache[client.CACHE_KEY][0]["title"] == "Backend Software Engineer"
    # Full description is deliberately not cached (keeps a session-cookie
    # cache small per TR-03's mitigation).
    assert "description" not in cache[client.CACHE_KEY][0]


def test_search_job_postings_requires_a_keyword():
    try:
        client.search_job_postings("   ", app_id="id", app_key="key")
        assert False, "expected JobSearchError"
    except client.JobSearchError as exc:
        assert "keyword" in str(exc).lower()


def test_search_job_postings_requires_credentials(monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)

    try:
        client.search_job_postings("engineer", app_id=None, app_key=None)
        assert False, "expected JobSearchError"
    except client.JobSearchError as exc:
        assert "not configured" in str(exc).lower()


def test_search_job_postings_raises_on_zero_results(monkeypatch):
    monkeypatch.setattr(
        client.requests, "get", lambda *a, **k: FakeResponse({"results": []})
    )

    try:
        client.search_job_postings("zzz-nonexistent-role", app_id="id", app_key="key")
        assert False, "expected JobSearchError"
    except client.JobSearchError as exc:
        assert "no job postings matched" in str(exc).lower()


def test_search_job_postings_falls_back_to_cache_on_api_failure(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(client.requests, "get", _raise)
    cache = {
        client.CACHE_KEY: [
            {"title": "Cached Role", "company": "Cached Co", "summary": "A cached summary."}
        ]
    }

    response = client.search_job_postings(
        "engineer", app_id="id", app_key="key", cache=cache
    )

    assert response.from_cache is True
    assert response.warning is not None
    assert response.results[0].title == "Cached Role"


def test_search_job_postings_raises_on_api_failure_without_cache(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(client.requests, "get", _raise)

    try:
        client.search_job_postings("engineer", app_id="id", app_key="key", cache={})
        assert False, "expected JobSearchError"
    except client.JobSearchError as exc:
        assert "job description manually" in str(exc).lower()
