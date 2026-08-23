"""Resume / JD Ingestion & Parser component (Component Diagram, Figure 5).

Fully implemented in WP-02 — see `parser.py` for FR-01, FR-05, and FR-06.
"""
from .parser import (
    IngestionError,
    IngestionResult,
    extract_job_description_text,
    extract_resume_text,
    extract_role,
    extract_skills,
    ingest,
)

__all__ = [
    "IngestionError",
    "IngestionResult",
    "extract_job_description_text",
    "extract_resume_text",
    "extract_role",
    "extract_skills",
    "ingest",
]
