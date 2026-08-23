"""Integration tests for the Web UI's ingestion routes (WP-02).

Exercises the same flows as Table 9's manual test cases (TC-01, TC-05) but
through the actual Flask routes, end to end.
"""
from __future__ import annotations

import io


def test_index_renders_upload_form(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"resume" in response.data.lower()
    assert b"job_description" in response.data


def test_ingest_view_returns_extracted_skills_and_role(
    client, sample_resume_pdf_bytes, sample_job_description_text
):
    """TC-03-adjacent: successful ingestion of resume + JD via the web form."""
    data = {
        "resume": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf"),
        "job_description": sample_job_description_text,
    }

    response = client.post(
        "/ingest", data=data, content_type="multipart/form-data"
    )

    assert response.status_code == 200
    body = response.data.decode()
    assert "Backend Software Engineer" in body
    assert "Python" in body


def test_ingest_view_rejects_missing_resume(client, sample_job_description_text):
    data = {"job_description": sample_job_description_text}

    response = client.post(
        "/ingest", data=data, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    assert b"resume file" in response.data.lower()


def test_ingest_view_rejects_unsupported_resume_type(
    client, sample_job_description_text
):
    """TC-05: unsupported file type shows a clear error, no server crash."""
    data = {
        "resume": (io.BytesIO(b"just text"), "resume.txt"),
        "job_description": sample_job_description_text,
    }

    response = client.post(
        "/ingest", data=data, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    assert b"Unsupported file type" in response.data


def test_ingest_view_requires_a_job_description(client, sample_resume_pdf_bytes):
    data = {"resume": (io.BytesIO(sample_resume_pdf_bytes), "resume.pdf")}

    response = client.post(
        "/ingest", data=data, content_type="multipart/form-data"
    )

    assert response.status_code == 400
    assert b"job description" in response.data.lower()
