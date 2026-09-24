"""Answer Evaluator component (Component Diagram, Figure 5) — WP-06.

See `evaluator.py` for FR-11 and FR-12.
"""
from .evaluator import AnswerEvaluationError, EvaluationResult, evaluate_answer

__all__ = ["AnswerEvaluationError", "EvaluationResult", "evaluate_answer"]
