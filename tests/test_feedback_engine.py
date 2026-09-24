"""Unit tests for the Feedback & Scoring Engine component (WP-07): FR-13."""
from __future__ import annotations

import pytest

from app.answer_evaluator import EvaluationResult
from app.extensions import db
from app.feedback_engine import ScoringError, compute_overall_score, record_feedback
from app.session_store.models import Answer, InterviewSession, JobPosting, Question, Resume


def _make_session_with_questions(n=2):
    resume = Resume(file_name="r.pdf", extracted_text="...", extracted_skills="[]")
    job_posting = JobPosting(title="Engineer", description="...", source="manual")
    interview_session = InterviewSession(resume=resume, job_posting=job_posting)
    db.session.add(interview_session)
    questions = []
    for i in range(n):
        q = Question(session=interview_session, text=f"Q{i}", type="behavioral", order_index=i)
        db.session.add(q)
        questions.append(q)
    db.session.commit()
    return interview_session, questions


def test_record_feedback_persists_a_feedback_row(app):
    with app.app_context():
        interview_session, (question,) = _make_session_with_questions(1)
        answer = Answer(question=question, text="my answer", input_mode="text")
        db.session.add(answer)
        db.session.commit()

        feedback = record_feedback(
            answer, EvaluationResult(score=77, strengths="s", weaknesses="w", suggestions="sug")
        )

        assert feedback.id is not None
        assert answer.feedback.score == 77


def test_compute_overall_score_averages_all_answers(app):
    with app.app_context():
        interview_session, questions = _make_session_with_questions(2)
        for question, score in zip(questions, [80, 60]):
            answer = Answer(question=question, text="answer", input_mode="text")
            db.session.add(answer)
            db.session.commit()
            record_feedback(
                answer, EvaluationResult(score=score, strengths="", weaknesses="", suggestions="s")
            )

        report = compute_overall_score(interview_session)

        assert report.overall_score == 70
        assert interview_session.readiness_report.overall_score == 70


def test_compute_overall_score_raises_if_a_question_is_unanswered(app):
    with app.app_context():
        interview_session, (question,) = _make_session_with_questions(1)

        with pytest.raises(ScoringError, match="not been answered"):
            compute_overall_score(interview_session)


def test_compute_overall_score_raises_for_a_session_with_no_questions(app):
    with app.app_context():
        resume = Resume(file_name="r.pdf", extracted_text="...", extracted_skills="[]")
        job_posting = JobPosting(title="Engineer", description="...", source="manual")
        interview_session = InterviewSession(resume=resume, job_posting=job_posting)
        db.session.add(interview_session)
        db.session.commit()

        with pytest.raises(ScoringError, match="no answered questions"):
            compute_overall_score(interview_session)
