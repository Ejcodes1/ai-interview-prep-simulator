"""Shared pytest fixtures.

Resume/DOCX/PDF fixtures are generated in-memory with reportlab and
python-docx rather than committed as binary files, so the sample content
(and the skills/role it must yield) stays visible and editable right next
to the tests that assert on it.

The resume and job description content below is the canonical test data
specified in the Phase 1 report v4, Section 9 (Table 9): a single sample
resume for a junior backend developer with two internships, and a single
matching job posting, reused across the relevant test cases (TC-01 through
TC-04) so scoring/extraction behavior is comparable across tests instead of
each using its own generic placeholder text.
"""
from __future__ import annotations

import io

import docx
import pytest
from reportlab.pdfgen import canvas

from app import create_app
from app.extensions import db

# Table 9: "Resume_JaneDoe_JuniorBackendDev.pdf — a 2-page PDF resume for a
# junior backend developer, listing Python, Flask, SQL, and Git skills plus
# two internships."
SAMPLE_RESUME_FILENAME = "Resume_JaneDoe_JuniorBackendDev.pdf"

SAMPLE_RESUME_TEXT_LINES = [
    "Jane Doe",
    "jane.doe@example.com",
    "Junior Backend Developer",
    "Skills: Python, Flask, SQL, Git, REST APIs, Communication, Teamwork.",
    "Internship, Brightline Analytics (Summer 2025)",
    "Built REST API endpoints in Python and Flask; wrote SQL queries against",
    "a PostgreSQL database.",
    "Internship, Northgate Software (Summer 2024)",
    "Used Git for version control and took part in Agile team ceremonies.",
    "B.S. Computer Science, State University (2026)",
]

# Table 9: "Junior Backend Developer — Python, Flask, REST APIs, SQL, Git,
# 0-2 years' experience."
SAMPLE_JOB_DESCRIPTION_TEXT = """Job Title: Junior Backend Developer
We are hiring a Junior Backend Developer. Required skills: Python, Flask,
REST APIs, SQL, and Git. 0-2 years' experience preferred. The ideal
candidate is a strong communicator who enjoys Agile teamwork.
"""


def make_pdf_bytes(lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    y = 800
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 20
    pdf.save()
    return buffer.getvalue()


def make_docx_bytes(lines: list[str]) -> bytes:
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture(scope="session")
def sample_resume_filename() -> str:
    return SAMPLE_RESUME_FILENAME


@pytest.fixture(scope="session")
def sample_resume_pdf_bytes() -> bytes:
    return make_pdf_bytes(SAMPLE_RESUME_TEXT_LINES)


@pytest.fixture(scope="session")
def sample_resume_docx_bytes() -> bytes:
    return make_docx_bytes(SAMPLE_RESUME_TEXT_LINES)


@pytest.fixture(scope="session")
def sample_job_description_text() -> str:
    return SAMPLE_JOB_DESCRIPTION_TEXT


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
