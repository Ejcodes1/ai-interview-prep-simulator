"""Answer Evaluator component — STUB (planned for WP-06).

Per the Component Diagram (Figure 5), this component receives a typed
answer directly from the Web UI, or a transcript from the Speech-to-Text
Transcriber, and calls the LLM API to score it. Its output feeds the
Feedback & Scoring Engine.

Covers: FR-11 (score each answer for relevance, clarity, use of examples),
FR-12 (per-question feedback with at least one improvement suggestion).

Credentials: OPENAI_API_KEY, read from the environment via `app.config`
(see .env.example). Respect NFR-07 (MAX_LLM_CALLS_PER_SESSION).

Not implemented yet — calling `evaluate_answer` raises NotImplementedError.
"""
from __future__ import annotations

from dataclasses import dataclass


class AnswerEvaluationError(Exception):
    """Raised when the LLM call fails or returns an unusable response."""


@dataclass
class EvaluationResult:
    """Shape a future implementation should return each evaluation as."""

    score: float  # e.g. 0-100
    strengths: str
    weaknesses: str
    suggestions: str


def evaluate_answer(question_text: str, answer_text: str) -> EvaluationResult:
    """Evaluate a submitted answer against a fixed rubric (FR-11, FR-12).

    TODO(WP-06):
      - Use a fixed evaluation rubric in the prompt template (relevance,
        clarity, use of concrete examples) — TR-01 mitigation.
      - Call the LLM API and parse the response into an EvaluationResult.
      - Return within 15 seconds (NFR-01) and include at least one concrete
        improvement suggestion (FR-12 acceptance criterion).
      - Raise AnswerEvaluationError with a user-facing message on failure
        (NFR-02), without crashing the session.
    """
    raise NotImplementedError("Answer evaluation is planned for WP-06.")
