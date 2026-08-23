"""Unit tests for the Resume/JD Ingestion & Parser component (WP-02).

Covers FR-01 (resume upload/text extraction), FR-05 (manual JD entry via
paste or upload), and FR-06 (role/skill extraction), plus the FR-16 clear
error messages required around invalid input. Test case IDs from the
Phase 1 report's Table 9 are referenced where they apply directly.
"""
from __future__ import annotations

import io

import pytest
from werkzeug.datastructures import FileStorage

from app.ingestion import parser


def _file_storage(data: bytes, filename: str) -> FileStorage:
    return FileStorage(stream=io.BytesIO(data), filename=filename)


# --- FR-01: resume upload + text extraction --------------------------------


def test_extract_resume_text_from_pdf(sample_resume_pdf_bytes):
    """TC-01: a valid PDF resume is accepted and its text is extracted."""
    file_storage = _file_storage(sample_resume_pdf_bytes, "resume.pdf")

    text = parser.extract_resume_text(file_storage)

    assert "Jane Doe" in text
    assert "Python" in text


def test_extract_resume_text_from_docx(sample_resume_docx_bytes):
    file_storage = _file_storage(sample_resume_docx_bytes, "resume.docx")

    text = parser.extract_resume_text(file_storage)

    assert "Jane Doe" in text
    assert "Flask" in text


def test_extract_resume_text_rejects_unsupported_extension():
    """TC-05: an unsupported file type produces a clear error, no crash."""
    file_storage = _file_storage(b"hello world", "resume.txt")

    with pytest.raises(parser.IngestionError, match="Unsupported file type"):
        parser.extract_resume_text(file_storage)


def test_extract_resume_text_rejects_empty_file():
    file_storage = _file_storage(b"", "resume.pdf")

    with pytest.raises(parser.IngestionError, match="empty"):
        parser.extract_resume_text(file_storage)


def test_extract_resume_text_rejects_corrupted_pdf():
    file_storage = _file_storage(b"not actually a pdf", "resume.pdf")

    with pytest.raises(parser.IngestionError, match="could not be read"):
        parser.extract_resume_text(file_storage)


def test_extract_resume_text_requires_a_file():
    with pytest.raises(parser.IngestionError, match="No file was provided"):
        parser.extract_resume_text(_file_storage(b"", ""))


# --- FR-05: manual job description entry (paste or upload) -----------------


def test_extract_job_description_text_from_pasted_text(sample_job_description_text):
    text = parser.extract_job_description_text(text=sample_job_description_text)

    assert text == sample_job_description_text.strip()


def test_extract_job_description_text_from_uploaded_txt_file():
    file_storage = _file_storage(b"We need a Python developer.", "jd.txt")

    text = parser.extract_job_description_text(file_storage=file_storage)

    assert "Python developer" in text


def test_extract_job_description_text_prefers_pasted_text_over_file():
    file_storage = _file_storage(b"from file", "jd.txt")

    text = parser.extract_job_description_text(
        text="from pasted text", file_storage=file_storage
    )

    assert text == "from pasted text"


def test_extract_job_description_text_requires_something():
    with pytest.raises(parser.IngestionError, match="Please paste"):
        parser.extract_job_description_text()


def test_extract_job_description_text_rejects_unsupported_file_extension():
    file_storage = _file_storage(b"binary junk", "jd.exe")

    with pytest.raises(parser.IngestionError, match="Unsupported file type"):
        parser.extract_job_description_text(file_storage=file_storage)


# --- FR-06: role/skill extraction -------------------------------------------


def test_extract_skills_finds_at_least_five_from_lexicon(sample_job_description_text):
    skills = parser.extract_skills(sample_job_description_text)

    assert len(skills) >= 5
    assert "Python" in skills
    assert "Docker" in skills


def test_extract_skills_uses_frequency_fallback_when_lexicon_is_sparse():
    text = "Zylotech Streamforge Quantivar Brightpath Nordwave is a company."

    skills = parser.extract_skills(text, min_skills=3)

    assert len(skills) >= 3


def test_extract_skills_returns_empty_for_blank_text():
    assert parser.extract_skills("") == []


def test_extract_role_finds_labelled_title():
    role = parser.extract_role("Job Title: Backend Software Engineer\nMore text.")

    assert role == "Backend Software Engineer"


def test_extract_role_falls_back_to_first_short_line():
    role = parser.extract_role("Backend Software Engineer\nWe are hiring.")

    assert role == "Backend Software Engineer"


def test_extract_role_returns_none_for_empty_text():
    assert parser.extract_role("") is None


# --- Full pipeline (FR-01 + FR-05 + FR-06 together) -------------------------


def test_ingest_combines_resume_and_job_description(
    sample_resume_pdf_bytes, sample_job_description_text
):
    resume_file = _file_storage(sample_resume_pdf_bytes, "resume.pdf")

    result = parser.ingest(
        resume_file, job_description_text=sample_job_description_text
    )

    assert "Jane Doe" in result.resume_text
    assert "Acme Corp" in result.job_description_text
    assert len(result.skills) >= 5
    assert result.role == "Backend Software Engineer"


def test_ingest_raises_on_missing_job_description(sample_resume_pdf_bytes):
    resume_file = _file_storage(sample_resume_pdf_bytes, "resume.pdf")

    with pytest.raises(parser.IngestionError):
        parser.ingest(resume_file)
