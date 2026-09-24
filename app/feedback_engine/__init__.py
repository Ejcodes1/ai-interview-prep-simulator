"""Feedback & Scoring Engine component (Component Diagram, Figure 5) — WP-07.

See `engine.py` for FR-13 and FR-14.
"""
from .engine import ScoringError, compute_overall_score, record_feedback

__all__ = ["ScoringError", "compute_overall_score", "record_feedback"]
