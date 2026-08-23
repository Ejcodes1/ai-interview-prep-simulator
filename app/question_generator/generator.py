"""Question Generator component — STUB (planned for WP-04).

Per the Component Diagram (Figure 5), this component sits between the two
ingestion paths and the rest of the flow: it receives the combined output
of the Resume/JD Ingestion & Parser (WP-02, already implemented) and the
Job Search Module (WP-03), calls the LLM API to produce tailored questions,
and reads from/writes to the Session Store (dashed arrow) to persist them
against the current InterviewSession.

Covers: FR-06 (role/skill extraction is already done upstream by
`app.ingestion.parser.extract_skills`; this module additionally uses that
plus resume/JD text to prompt the LLM), FR-07 (generate >= 5 tailored
questions mixing behavioral and technical types), FR-08 (question order
persisted for the one-at-a-time session flow).

Credentials: OPENAI_API_KEY, read from the environment via `app.config`
(see .env.example). Respect NFR-07 (MAX_LLM_CALLS_PER_SESSION) once
implemented.

Not implemented yet — calling `generate_questions` raises NotImplementedError.
"""
from __future__ import annotations

from dataclasses import dataclass


class QuestionGenerationError(Exception):
    """Raised when the LLM call fails or returns an unusable response."""


@dataclass
class QuestionDraft:
    """Shape a future implementation should return each question as."""

    text: str
    type: str  # "behavioral" or "technical"
    order_index: int


def generate_questions(
    resume_text: str,
    job_description_text: str,
    skills: list[str],
    min_questions: int = 5,
) -> list[QuestionDraft]:
    """Generate a tailored set of interview questions (FR-07).

    TODO(WP-04):
      - Build a prompt combining resume_text, job_description_text, and the
        extracted `skills` (from app.ingestion.parser.extract_skills).
      - Call the LLM API (OpenAI), enforcing a fixed evaluation/generation
        rubric in the prompt template (TR-01 mitigation).
      - Parse the response into >= `min_questions` QuestionDraft entries,
        mixing "behavioral" and "technical" types (FR-07 acceptance
        criterion).
      - Persist the drafts as Question rows via the Session Store, tied to
        the current InterviewSession, preserving order_index (FR-08).
      - Complete within 10 seconds (NFR-01) and raise QuestionGenerationError
        with a user-facing message on failure (NFR-02).
    """
    raise NotImplementedError("Question generation is planned for WP-04.")
