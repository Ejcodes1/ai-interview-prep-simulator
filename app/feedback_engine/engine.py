"""Feedback & Scoring Engine component (WP-07).

Per the Component Diagram (Figure 5, Phase 1 report v4), this component is
one of three that read from and write to the Session Store directly (the
other two being the Question Generator and the PDF Report Generator — the
Answer Evaluator itself never writes to the Session Store; it hands its
output to this component instead). Concretely: as each answer is scored,
`record_feedback` writes that answer's per-question feedback and score to
the Session Store; once every question in the session has been answered,
`compute_overall_score` reads back the full set of per-question scores to
compute and persist the aggregate readiness score.

Covers: FR-13 (compute and display an overall 0-100 readiness score),
FR-14 (assemble the full session review: questions, answers, and scores).
"""
from __future__ import annotations

from app.answer_evaluator import EvaluationResult
from app.extensions import db
from app.session_store.models import Answer, Feedback, InterviewSession, ReadinessReport


class ScoringError(Exception):
    """Raised when a session has no scored answers to aggregate."""


def record_feedback(answer: Answer, evaluation: EvaluationResult) -> Feedback:
    """Persist one answer's evaluation as a Feedback row (FR-12)."""
    feedback = Feedback(
        answer=answer,
        score=evaluation.score,
        strengths=evaluation.strengths,
        weaknesses=evaluation.weaknesses,
        suggestions=evaluation.suggestions,
    )
    db.session.add(feedback)
    db.session.commit()
    return feedback


def compute_overall_score(session: InterviewSession) -> ReadinessReport:
    """Aggregate every answer's score into one 0-100 readiness score (FR-13).

    Reads back the Feedback rows written by `record_feedback` for every
    Question in the session; raises ScoringError if any question has not
    yet been answered and scored.
    """
    scores: list[float] = []
    for question in session.questions:
        if question.answer is None or question.answer.feedback is None:
            raise ScoringError(
                f"Question {question.id} has not been answered and scored yet."
            )
        scores.append(question.answer.feedback.score)

    if not scores:
        raise ScoringError("This session has no answered questions to score.")

    overall_score = sum(scores) / len(scores)

    report = session.readiness_report
    if report is None:
        report = ReadinessReport(session=session, overall_score=overall_score)
        db.session.add(report)
    else:
        report.overall_score = overall_score

    db.session.commit()
    return report
