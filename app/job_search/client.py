"""Job Search Module — STUB (planned for WP-03).

Per the System Context Diagram (Figure 4) and Component Diagram (Figure 5),
this module wraps a job search API (Adzuna, with The Muse as a documented
fallback per TR-03) so a candidate can search postings by title/keyword and
select one to auto-populate the job description field, instead of pasting
one manually via the Resume/JD Ingestion & Parser (FR-05).

Covers: FR-02 (search by keyword), FR-03 (display results), FR-04 (select a
result to populate the JD field).

Credentials: ADZUNA_APP_ID / ADZUNA_APP_KEY, read from the environment via
`app.config` (see .env.example). Not required until this module is
implemented.

Not implemented yet — calling `search_job_postings` raises NotImplementedError.
"""
from __future__ import annotations

from dataclasses import dataclass


class JobSearchError(Exception):
    """Raised when the job search API call fails or is misconfigured."""


@dataclass
class JobPostingResult:
    """Shape a future implementation should return one match as."""

    title: str
    company: str
    summary: str
    description: str
    source: str = "adzuna"


def search_job_postings(keyword: str, location: str | None = None) -> list[JobPostingResult]:
    """Search job postings by title/keyword (FR-02).

    TODO(WP-03):
      - Call the Adzuna "search" endpoint using ADZUNA_APP_ID / ADZUNA_APP_KEY.
      - Map each result to a JobPostingResult (FR-03: title, company, summary).
      - Return at least one match within 5 seconds (FR-02 acceptance criterion).
      - On API failure/timeout, raise JobSearchError with a user-facing
        message and let the caller fall back to manual JD entry (FR-05, TR-03).
    """
    raise NotImplementedError(
        "Job search is planned for WP-03. Use manual job description entry "
        "(FR-05, app.ingestion.parser.extract_job_description_text) for now."
    )
