"""Job Search Module (Component Diagram, Figure 5) — implemented in WP-03.

See `client.py` for FR-02, FR-03, and FR-04.
"""
from .client import JobPostingResult, JobSearchError, JobSearchResponse, search_job_postings

__all__ = [
    "JobPostingResult",
    "JobSearchError",
    "JobSearchResponse",
    "search_job_postings",
]
