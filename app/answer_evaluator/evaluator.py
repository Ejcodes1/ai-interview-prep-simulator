"""Answer Evaluator component (WP-06).

Per the Component Diagram (Figure 5), this component receives a typed
answer directly from the Web UI, or a transcript from the Speech-to-Text
Transcriber, and calls the LLM API to score it against a fixed rubric. Its
output is handed to the Feedback & Scoring Engine, which is the sole
writer of Feedback rows — this component itself never writes to the
Session Store.

Covers: FR-11 (score each answer for relevance, clarity, use of examples),
FR-12 (per-question feedback with at least one improvement suggestion).

Respects NFR-01 (feedback within 15 seconds) via a request timeout, and
uses a fixed rubric in the prompt template (TR-01 mitigation) rather than
letting the model free-form its own criteria.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from app.env_utils import clean_env

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 15  # NFR-01: answer feedback within 15 seconds.

_SYSTEM_PROMPT = """You are an interview-answer evaluator for a job-interview \
practice tool. Score the candidate's answer to the given interview question \
against this fixed rubric:

- Relevance: does the answer actually address the question asked?
- Clarity: is the answer well-structured and easy to follow?
- Concrete examples: does the answer use specific, concrete examples or \
details rather than vague generalities?

Respond with ONLY a JSON object of the exact shape:
{"score": <number 0-100>, "strengths": "...", "weaknesses": "...", \
"suggestions": "..."}

"suggestions" must contain at least one concrete, actionable improvement.
"""


class AnswerEvaluationError(Exception):
    """Raised when the LLM call fails or returns an unusable response."""


@dataclass
class EvaluationResult:
    score: float  # 0-100
    strengths: str
    weaknesses: str
    suggestions: str


def _build_client(client: OpenAI | None, timeout: float) -> OpenAI:
    if client is not None:
        return client
    api_key = clean_env("OPENAI_API_KEY")
    if not api_key:
        raise AnswerEvaluationError(
            "Answer evaluation is not configured (missing OPENAI_API_KEY)."
        )
    return OpenAI(api_key=api_key, timeout=timeout)


def evaluate_answer(
    question_text: str,
    answer_text: str,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> EvaluationResult:
    """Evaluate a submitted answer against a fixed rubric (FR-11, FR-12)."""
    if not answer_text or not answer_text.strip():
        raise AnswerEvaluationError("An answer is required before it can be evaluated.")

    resolved_model = model or clean_env("OPENAI_MODEL", DEFAULT_MODEL)

    user_prompt = f"Interview question:\n{question_text.strip()}\n\nCandidate's answer:\n{answer_text.strip()}"

    try:
        # Client construction is inside this block too: an incompatible
        # openai/httpx dependency pair, or any other environment issue,
        # must degrade to a clear message here rather than a raw 500.
        resolved_client = _build_client(client, timeout)
        response = resolved_client.chat.completions.create(
            model=resolved_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            timeout=timeout,
        )
    except AnswerEvaluationError:
        raise
    except Exception as exc:
        logger.error("Answer evaluation failed: %s: %s", type(exc).__name__, exc)
        raise AnswerEvaluationError(
            "The answer-evaluation service is temporarily unavailable. "
            "Please try again shortly."
        ) from exc

    raw_content = response.choices[0].message.content if response.choices else None
    if not raw_content:
        raise AnswerEvaluationError(
            "The answer-evaluation service returned an empty response."
        )

    try:
        payload = json.loads(raw_content)
        score = float(payload["score"])
        strengths = str(payload.get("strengths", "")).strip()
        weaknesses = str(payload.get("weaknesses", "")).strip()
        suggestions = str(payload.get("suggestions", "")).strip()
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise AnswerEvaluationError(
            "The answer-evaluation service returned an unusable response."
        ) from exc

    if not suggestions:
        raise AnswerEvaluationError(
            "The answer-evaluation service did not return an improvement suggestion."
        )

    score = max(0.0, min(100.0, score))

    return EvaluationResult(
        score=score, strengths=strengths, weaknesses=weaknesses, suggestions=suggestions
    )
