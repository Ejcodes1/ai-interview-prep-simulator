"""Integration tests for the Job Search Web UI routes (WP-03): FR-02-FR-04."""
from __future__ import annotations

import io

from app.job_search import client as job_search_client


class FakeResponse:
    def __init__(self, json_data=None, raise_exc=None):
        self._json_data = json_data or {}
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc

    def json(self):
        return self._json_data


PAYLOAD = {
    "results": [
        {
            "title": "Backend Software Engineer",
            "company": {"display_name": "Acme Corp"},
            "description": "Build and maintain REST APIs using Python and Flask.",
        }
    ]
}


def test_job_search_form_renders(client):
    response = client.get("/jobs/search")

    assert response.status_code == 200
    assert b"keyword" in response.data


def test_job_search_view_shows_results(client, monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_ID", "test-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "test-key")
    monkeypatch.setattr(
        job_search_client.requests, "get", lambda *a, **k: FakeResponse(PAYLOAD)
    )

    response = client.post("/jobs/search", data={"keyword": "software engineer"})

    assert response.status_code == 200
    assert b"Backend Software Engineer" in response.data
    assert b"Acme Corp" in response.data


def test_job_search_view_missing_credentials_shows_clear_error(client, monkeypatch):
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)

    response = client.post("/jobs/search", data={"keyword": "engineer"})

    assert response.status_code == 400
    assert b"not configured" in response.data.lower()


def test_job_search_view_requires_keyword(client):
    response = client.post("/jobs/search", data={"keyword": "  "})

    assert response.status_code == 400
    assert b"keyword" in response.data.lower()


def test_job_select_view_prefills_index_form(client):
    response = client.post(
        "/jobs/select",
        data={
            "title": "Backend Software Engineer",
            "company": "Acme Corp",
            "description": "Build and maintain REST APIs.",
        },
    )

    assert response.status_code == 200
    body = response.data.decode()
    assert "Backend Software Engineer" in body
    assert "Build and maintain REST APIs." in body


def test_full_select_flow_can_be_ingested(client, sample_resume_pdf_bytes):
    """FR-04: a selected posting's description flows straight into /ingest."""
    select_response = client.post(
        "/jobs/select",
        data={
            "title": "Backend Software Engineer",
            "company": "Acme Corp",
            "description": "Looking for a Python and Flask developer with SQL and Docker experience.",
        },
    )
    assert b"Python and Flask developer" in select_response.data

    ingest_response = client.post(
        "/ingest",
        data={
            "resume": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf"),
            "job_description": "Looking for a Python and Flask developer with SQL and Docker experience.",
        },
        content_type="multipart/form-data",
    )

    assert ingest_response.status_code == 200
    assert b"Python" in ingest_response.data
