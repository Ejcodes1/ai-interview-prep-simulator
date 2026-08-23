"""PDF Report Generator component — STUB (planned for WP-07).

Per the Component Diagram (Figure 5), this component receives the
aggregated results from the Feedback & Scoring Engine and renders them as
a downloadable PDF (Section 6: ReadinessReport.pdfPath).

Covers: FR-15 (export a feedback report as PDF containing questions,
answers, scores, and suggestions).

Uses the `reportlab` library (see requirements.txt / Section 8).

Not implemented yet — calling `generate_pdf_report` raises NotImplementedError.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class ReportGenerationError(Exception):
    """Raised when the PDF cannot be generated or written to disk."""


@dataclass
class SessionReportData:
    """Everything FR-15 requires the exported PDF to contain."""

    overall_score: float
    questions: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def generate_pdf_report(data: SessionReportData, output_path: str) -> str:
    """Render the session's feedback as a downloadable PDF (FR-15).

    TODO(WP-07):
      - Use reportlab to lay out `data` (questions, answers, scores,
        suggestions) as a readable document.
      - Write the PDF to `output_path` and return that path so it can be
        stored on ReadinessReport.pdf_path (Session Store).
      - Raise ReportGenerationError with a user-facing message on failure.
    """
    raise NotImplementedError("PDF report export is planned for WP-07.")
