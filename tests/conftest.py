"""Shared pytest fixtures.

Resume/DOCX/PDF fixtures are generated in-memory with reportlab and
python-docx rather than committed as binary files, so the sample content
(and the skills/role it must yield) stays visible and editable right next
to the tests that assert on it.
"""
from __future__ import annotations

import io

import docx
import pytest
from reportlab.pdfgen import canvas

from app import create_app
from app.extensions import db

SAMPLE_RESUME_TEXT_LINES = [
    "Jane Doe",
    "jane.doe@example.com",
    "Software Engineer with 4 years of experience.",
    "Skills: Python, Flask, SQL, Docker, Git, Communication, Teamwork.",
    "Built REST API services and led a small team using Agile practices.",
]

SAMPLE_JOB_DESCRIPTION_TEXT = """Job Title: Backend Software Engineer
Acme Corp is hiring a Backend Software Engineer.
Required skills: Python, SQL, AWS, Docker, Kubernetes.
The ideal candidate has strong Communication and Leadership skills,
practices Agile/Scrum, and enjoys Problem Solving.
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
