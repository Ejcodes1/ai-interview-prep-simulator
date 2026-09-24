"""PDF Report Generator component (Component Diagram, Figure 5) — WP-07.

See `generator.py` for FR-15.
"""
from .generator import ReportGenerationError, generate_pdf_report

__all__ = ["ReportGenerationError", "generate_pdf_report"]
