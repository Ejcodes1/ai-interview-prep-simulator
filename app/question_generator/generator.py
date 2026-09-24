"""Question Generator component (WP-04).

Per the Component Diagram (Figure 5), this component receives the combined
output of the Resume/JD Ingestion & Parser (WP-02) and the Job Search
Module (WP-03), calls the LLM API to produce tailored questions, and is one
of three components (alongside the Feedback & Scoring Engine and the PDF
Report Generator) that read from and write to the Session Store directly —
here, the caller persists the returned QuestionDraft list as Question rows
tied to the current InterviewSession.

Covers: FR-07 (generate >= 5 tailored questions mixing behavioral and
technical types), FR-08 (question order is preserved for the one-at-a-time
session flow via order_index).

Uses a fixed prompt template (rubric baked into the system prompt) per the
TR-01 mitigation, rather than letting the model freewheel on format.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 10  # NFR-01: question generation completes within 10s.
DEFAULT_MIN_QUESTIONS = 5

_SYSTEM_PROMPT = """You are an interview-question generator for a job-interview \
practice tool. Given a candidate's resume text, a target job description, and a \
list of extracted skills, generate a tailored set of interview questions.

Rules:
- Generate at least {min_questions} questions.
- Mix "behavioral" questions (ask the candidate to describe how they handled a \
past situation, evaluable with the STAR method) and "technical" questions (assess \
role-specific knowledge or skills relevant to the job description and skills list).
- Every question must be specific to the candidate's actual resume content and/or \
the job description — do not ask generic questions that could apply to any candidate.
- Respond with ONLY a JSON object of the exact shape:
  {{"questions": [{{"text": "...", "type": "behavioral"}}, {{"text": "...", "type": "technical"}}, ...]}}
- "type" must be exactly "behavioral" or "technical" for every question.
"""


class QuestionGenerationError(Exception):
    """Raised when the LLM call fails or returns an unusable response."""


@dataclass
class QuestionDraft:
    text: str
    type: str  # "behavioral" or "technical"
    order_index: int


def _build_client(client: OpenAI | None, timeout: float) -> OpenAI:
    if client is not None:
        return client
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise QuestionGenerationError(
            "Question generation is not configured (missing OPENAI_API_KEY). "
            "Add a real key to .env to enable it."
        )
    return OpenAI(api_key=api_key, timeout=timeout)


def generate_questions(
    resume_text: str,
    job_description_text: str,
    skills: list[str],
    min_questions: int = DEFAULT_MIN_QUESTIONS,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[QuestionDraft]:
    """Generate a tailored set of interview questions (FR-07).

    Raises QuestionGenerationError on any failure (missing/invalid API key,
    network/timeout error, or a malformed/incomplete model response) so the
    caller can show a clear message instead of crashing (NFR-02).
    """
    if not resume_text or not resume_text.strip():
        raise QuestionGenerationError("Resume text is required to generate questions.")
    if not job_description_text or not job_description_text.strip():
        raise QuestionGenerationError("A job description is required to generate questions.")

    resolved_model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)

    skills_line = ", ".join(skills) if skills else "(none extracted)"
    user_prompt = (
        f"Resume:\n{resume_text.strip()}\n\n"
        f"Job description:\n{job_description_text.strip()}\n\n"
        f"Extracted skills: {skills_line}"
    )

    try:
        # Client construction is inside this block too: an incompatible
        # openai/httpx dependency pair, or any other environment issue,
        # must degrade to a clear message here rather than a raw 500.
        resolved_client = _build_client(client, timeout)
        response = resolved_client.chat.completions.create(
            model=resolved_model,
            messages=[
                {
                    "role": "system",
                    "content": _SYSTEM_PROMPT.format(min_questions=min_questions),
                },
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            timeout=timeout,
        )
    except QuestionGenerationError:
        raise
    except Exception as exc:
        logger.error("Question generation failed: %s: %s", type(exc).__name__, exc)
        raise QuestionGenerationError(
            "The question-generation service is temporarily unavailable. "
            "Please try again shortly."
        ) from exc

    raw_content = response.choices[0].message.content if response.choices else None
    if not raw_content:
        raise QuestionGenerationError(
            "The question-generation service returned an empty response."
        )

    try:
        payload = json.loads(raw_content)
        raw_questions = payload["questions"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise QuestionGenerationError(
            "The question-generation service returned an unusable response."
        ) from exc

    drafts: list[QuestionDraft] = []
    for index, item in enumerate(raw_questions):
        text = (item.get("text") or "").strip() if isinstance(item, dict) else ""
        q_type = (item.get("type") or "").strip().lower() if isinstance(item, dict) else ""
        if not text or q_type not in ("behavioral", "technical"):
            continue
        drafts.append(QuestionDraft(text=text, type=q_type, order_index=index))

    if len(drafts) < min_questions:
        raise QuestionGenerationError(
            f"Only {len(drafts)} usable questions were generated; expected at "
            f"least {min_questions}. Please try again."
        )

    return drafts
