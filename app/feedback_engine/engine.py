"""Feedback & Scoring Engine component — STUB (planned for WP-07).

Per the Component Diagram (Figure 5, Phase 1 report v4), this component is
one of three that read from and write to the Session Store directly (the
other two being the Question Generator and the PDF Report Generator — the
Answer Evaluator itself never writes to the Session Store; it hands its
output to this component instead). Concretely: as each answer is scored,
this component writes that answer's per-question feedback and score back
to the Session Store, then — once every question in the session has been
answered — reads back the full set of per-question scores to compute the
aggregate readiness score.

Covers: FR-13 (compute and display an overall 0-100 readiness score),
FR-14 (assemble the full session review: questions, answers, and scores).

Not implemented yet — calling `compute_overall_score` raises NotImplementedError.
"""
from __future__ import annotations


class ScoringError(Exception):
    """Raised when a session has no scored answers to aggregate."""


def compute_overall_score(per_answer_scores: list[float]) -> float:
    """Aggregate per-answer scores into one 0-100 readiness score (FR-13).

    TODO(WP-07):
      - As each app.answer_evaluator.evaluator.EvaluationResult is produced,
        write it to the Session Store as a Feedback row (Section 6 domain
        model) tied to its Answer.
      - Decide the aggregation rule (e.g. mean of per-answer scores) and
        raise ScoringError if `per_answer_scores` is empty (a session with
        zero answered questions cannot be scored).
      - Read back the full question/answer/feedback list for the session
        (FR-14) plus the aggregate score, and pass both to
        app.report_generator for PDF export (FR-15).
    """
    raise NotImplementedError("Score aggregation is planned for WP-07.")
