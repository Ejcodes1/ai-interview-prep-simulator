"""Smoke tests for the Session Store schema (Section 6 domain model).

These aren't part of WP-02 proper (the Ingestion module doesn't write to
the Session Store per the Component Diagram), but they confirm the
scaffolded schema round-trips the full Candidate -> InterviewSession ->
Resume/JobPosting/Question -> Answer -> Feedback -> ReadinessReport chain
before any later work package builds on it.
"""
from __future__ import annotations

from app.extensions import db
from app.session_store.models import (
    Answer,
    Candidate,
    Feedback,
    InterviewSession,
    JobPosting,
    Question,
    ReadinessReport,
    Resume,
)


def test_full_domain_model_chain_persists(app):
    with app.app_context():
        candidate = Candidate(name="Jane Doe", email="jane@example.com")
        resume = Resume(file_name="resume.pdf", extracted_text="...", extracted_skills="[]")
        job_posting = JobPosting(title="Backend Engineer", description="...", source="manual")
        session = InterviewSession(
            candidate=candidate, resume=resume, job_posting=job_posting
        )
        question = Question(session=session, text="Tell me about yourself.", type="behavioral", order_index=0)
        answer = Answer(question=question, text="I have 4 years of experience.", input_mode="text")
        feedback = Feedback(answer=answer, score=85.0, strengths="Clear", weaknesses="Brief", suggestions="Add an example.")
        report = ReadinessReport(session=session, overall_score=85.0)

        db.session.add_all([candidate, resume, job_posting, session, question, answer, feedback, report])
        db.session.commit()

        assert session.id is not None
        assert session.candidate_id == candidate.id
        assert session.resume.file_name == "resume.pdf"
        assert session.job_posting.title == "Backend Engineer"
        assert session.questions[0].answer.feedback.score == 85.0
        assert session.readiness_report.overall_score == 85.0
