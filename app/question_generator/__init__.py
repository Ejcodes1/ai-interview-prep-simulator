"""Question Generator component (Component Diagram, Figure 5) — WP-04.

See `generator.py` for FR-07 and FR-08.
"""
from .generator import QuestionDraft, QuestionGenerationError, generate_questions

__all__ = ["QuestionDraft", "QuestionGenerationError", "generate_questions"]
