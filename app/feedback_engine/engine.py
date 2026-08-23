"""Feedback & Scoring Engine component — STUB (planned for WP-07).

Per the Component Diagram (Figure 5), this component takes the Answer
Evaluator's per-answer scores for a session, aggregates them into a single
overall readiness score, and hands the result to the PDF Report Generator.
It is pure aggregation logic — no external API calls.

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
      - Decide the aggregation rule (e.g. mean of per-answer scores from
        app.answer_evaluator.evaluator.EvaluationResult.score).
      - Raise ScoringError if `per_answer_scores` is empty (a session with
        zero answered questions cannot be scored).
      - Feed the result, plus the full question/answer/feedback list
        (FR-14), into app.report_generator for PDF export (FR-15).
    """
    raise NotImplementedError("Score aggregation is planned for WP-07.")
