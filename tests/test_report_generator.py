"""Unit tests for the PDF Report Generator component (WP-07): FR-15."""
from __future__ import annotations

import os

import pytest

from app.answer_evaluator import EvaluationResult
from app.extensions import db
from app.feedback_engine import compute_overall_score, record_feedback
from app.report_generator import ReportGenerationError, generate_pdf_report
from app.session_store.models import Answer, InterviewSession, JobPosting, Question, Resume


def _make_scored_session():
    resume = Resume(file_name="r.pdf", extracted_text="...", extracted_skills="[]")
    job_posting = JobPosting(title="Junior Backend Developer", description="...", source="manual")
    interview_session = InterviewSession(resume=resume, job_posting=job_posting)
    db.session.add(interview_session)
    question = Question(session=interview_session, text="Tell me about a bug you fixed.", type="behavioral", order_index=0)
    db.session.add(question)
    db.session.commit()

    answer = Answer(question=question, text="I found and fixed a slow query.", input_mode="text")
    db.session.add(answer)
    db.session.commit()
    record_feedback(
        answer,
        EvaluationResult(score=85, strengths="Concrete example.", weaknesses="", suggestions="Quantify impact."),
    )
    compute_overall_score(interview_session)
    return interview_session


def test_generate_pdf_report_writes_a_file(app, tmp_path):
    with app.app_context():
        interview_session = _make_scored_session()

        output_path = generate_pdf_report(interview_session, str(tmp_path))

        assert os.path.exists(output_path)
        assert output_path.endswith(".pdf")
        assert os.path.getsize(output_path) > 0
        assert interview_session.readiness_report.pdf_path == output_path


def test_generate_pdf_report_requires_an_overall_score(app, tmp_path):
    with app.app_context():
        resume = Resume(file_name="r.pdf", extracted_text="...", extracted_skills="[]")
        job_posting = JobPosting(title="Engineer", description="...", source="manual")
        interview_session = InterviewSession(resume=resume, job_posting=job_posting)
        db.session.add(interview_session)
        db.session.commit()

        with pytest.raises(ReportGenerationError, match="no overall score"):
            generate_pdf_report(interview_session, str(tmp_path))
