"""PDF Report Generator component (WP-07).

Per the Component Diagram (Figure 5, Phase 1 report v4), this is the third
of three components that read from and write to the Session Store
directly: it reads the complete session record — questions, answers,
per-question feedback, and the aggregate score written by the Feedback &
Scoring Engine — to build the exported PDF, then writes the resulting
file's path back to the session (ReadinessReport.pdfPath, Section 6).

Covers: FR-15 (export a feedback report as PDF containing questions,
answers, scores, and suggestions).
"""
from __future__ import annotations

import os

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.extensions import db
from app.session_store.models import InterviewSession


class ReportGenerationError(Exception):
    """Raised when the PDF cannot be generated or written to disk."""


def generate_pdf_report(session: InterviewSession, output_dir: str) -> str:
    """Render the session's feedback as a downloadable PDF (FR-15).

    Requires every question in the session to already have a scored
    Feedback row (i.e. `feedback_engine.compute_overall_score` has already
    run for this session). Writes the PDF to
    `<output_dir>/<session_uuid>.pdf`, stores that path on the session's
    ReadinessReport, and returns it.
    """
    report = session.readiness_report
    if report is None:
        raise ReportGenerationError(
            "This session has no overall score yet; compute it before exporting."
        )

    try:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{session.session_uuid}.pdf")

        styles = getSampleStyleSheet()
        body = styles["BodyText"]
        heading = styles["Heading2"]
        label = ParagraphStyle("Label", parent=body, textColor="#14746a", spaceBefore=6)

        story = [
            Paragraph("AI Interview Prep Simulator — Readiness Report", styles["Title"]),
            Paragraph(f"Overall readiness score: {report.overall_score:.0f} / 100", styles["Heading1"]),
            Spacer(1, 0.2 * inch),
        ]

        if session.job_posting is not None:
            story.append(Paragraph(f"Role: {session.job_posting.title}", body))
            story.append(Spacer(1, 0.2 * inch))

        for index, question in enumerate(session.questions, start=1):
            answer = question.answer
            feedback = answer.feedback if answer else None

            story.append(Paragraph(f"Question {index} ({question.type})", heading))
            story.append(Paragraph(question.text, body))
            story.append(Spacer(1, 0.08 * inch))

            if answer is not None:
                story.append(Paragraph("Your answer:", label))
                story.append(Paragraph(answer.text, body))

            if feedback is not None:
                story.append(Paragraph(f"Score: {feedback.score:.0f} / 100", label))
                if feedback.strengths:
                    story.append(Paragraph(f"Strengths: {feedback.strengths}", body))
                if feedback.weaknesses:
                    story.append(Paragraph(f"Weaknesses: {feedback.weaknesses}", body))
                if feedback.suggestions:
                    story.append(Paragraph(f"Suggestion: {feedback.suggestions}", body))

            story.append(Spacer(1, 0.25 * inch))

        SimpleDocTemplate(output_path, pagesize=letter).build(story)
    except OSError as exc:
        raise ReportGenerationError(
            "The PDF report could not be written to disk."
        ) from exc

    report.pdf_path = output_path
    db.session.commit()

    return output_path
