"""Job Search Module (WP-03).

Per the System Context Diagram (Figure 4) and Component Diagram (Figure 5),
this module wraps the Adzuna job search API so a candidate can search
postings by title/keyword and select one to auto-populate the job
description field, instead of pasting one manually via the Resume/JD
Ingestion & Parser (FR-05).

Covers: FR-02 (search by keyword), FR-03 (display results: title, company,
short summary), FR-04 (select a result to populate the JD field — handled
by the Web UI route, which passes the selected result's full description
through untouched).

The Muse is documented in the Phase 1 report (Table 8) as an alternative
provider; it is not implemented here; swapping providers means adding a
sibling function behind this same JobPostingResult/JobSearchResponse shape
(BR-04 mitigation: each integration is isolated behind its own module).

Credentials: ADZUNA_APP_ID / ADZUNA_APP_KEY, read from the environment (see
.env.example) — never exposed to the client (NFR-06).

TR-03 mitigation: on API failure (timeout, rate limit, downtime), this
falls back to the last successful results passed in via `cache`, if any are
available; otherwise it raises JobSearchError so the caller can fall back
to manual JD entry (FR-05).
"""
from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field
from typing import Any, MutableMapping

import requests

from app.env_utils import clean_env

logger = logging.getLogger(__name__)

ADZUNA_SEARCH_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

# FR-02 acceptance criterion: a matching posting is returned within 5 seconds.
# Capping the request itself at 5s means a slow/hanging API can never
# silently blow past that budget — it fails fast into the cache/error path.
DEFAULT_TIMEOUT_SECONDS = 5
DEFAULT_RESULTS_PER_PAGE = 10
SUMMARY_MAX_LENGTH = 220

# How many results to keep in the TR-03 fallback cache. Kept small and
# lightweight (title/company/summary only, no full description) so it stays
# well under a browser cookie's size limit when `cache` is a Flask session.
MAX_CACHED_RESULTS = 5
CACHE_KEY = "job_search:last_successful_results"


class JobSearchError(Exception):
    """Raised when the job search API call fails, is misconfigured, or finds nothing."""


@dataclass
class JobPostingResult:
    """One matching posting (FR-03: title, company, summary)."""

    title: str
    company: str
    summary: str
    description: str
    source: str = "adzuna"


@dataclass
class JobSearchResponse:
    results: list[JobPostingResult] = field(default_factory=list)
    from_cache: bool = False
    warning: str | None = None


def _summarize(description: str, max_length: int = SUMMARY_MAX_LENGTH) -> str:
    """Collapse whitespace/HTML entities and truncate to a short summary."""
    text = html.unescape(" ".join(description.split()))
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(" ", 1)[0] + "…"


def _resolve_credentials(app_id: str | None, app_key: str | None) -> tuple[str | None, str | None]:
    # Read from the environment at call time (not import time) so
    # credentials set after process start, or monkeypatched in tests, work.
    return (
        app_id or clean_env("ADZUNA_APP_ID"),
        app_key or clean_env("ADZUNA_APP_KEY"),
    )


def _load_from_cache(cache: MutableMapping[str, Any] | None) -> list[JobPostingResult] | None:
    if cache is None:
        return None
    cached = cache.get(CACHE_KEY)
    if not cached:
        return None
    # Cached entries only ever store title/company/summary (see
    # _store_in_cache) — reuse the summary as the description too, since a
    # stale fallback result is better than none, per TR-03.
    return [
        JobPostingResult(
            title=item["title"],
            company=item["company"],
            summary=item["summary"],
            description=item["summary"],
        )
        for item in cached
    ]


def _store_in_cache(cache: MutableMapping[str, Any] | None, results: list[JobPostingResult]) -> None:
    if cache is None:
        return
    cache[CACHE_KEY] = [
        {"title": r.title, "company": r.company, "summary": r.summary}
        for r in results[:MAX_CACHED_RESULTS]
    ]


def search_job_postings(
    keyword: str,
    location: str | None = None,
    *,
    app_id: str | None = None,
    app_key: str | None = None,
    country: str | None = None,
    cache: MutableMapping[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> JobSearchResponse:
    """Search for job postings by title/keyword (FR-02).

    `cache` is any dict-like object (e.g. a Flask session) used to persist
    the last successful results across calls for the TR-03 fallback; pass
    None to disable caching (e.g. in tests that don't care about it).
    """
    if not keyword or not keyword.strip():
        raise JobSearchError("Please enter a keyword to search for job postings.")

    resolved_app_id, resolved_app_key = _resolve_credentials(app_id, app_key)
    if not resolved_app_id or not resolved_app_key:
        raise JobSearchError(
            "Job search is not configured (missing Adzuna API credentials). "
            "Enter a job description manually instead (FR-05)."
        )

    resolved_country = country or clean_env("ADZUNA_COUNTRY", "us")
    params = {
        "app_id": resolved_app_id,
        "app_key": resolved_app_key,
        "what": keyword.strip(),
        "results_per_page": DEFAULT_RESULTS_PER_PAGE,
        "content-type": "application/json",
    }
    if location and location.strip():
        params["where"] = location.strip()

    try:
        response = requests.get(
            ADZUNA_SEARCH_URL.format(country=resolved_country),
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        response_obj = getattr(exc, "response", None)
        logger.error(
            "Adzuna search failed: %s: %s (status=%s, body=%s)",
            type(exc).__name__,
            exc,
            getattr(response_obj, "status_code", None),
            (getattr(response_obj, "text", "") or "")[:300],
        )
        cached_results = _load_from_cache(cache)
        if cached_results:
            return JobSearchResponse(
                results=cached_results,
                from_cache=True,
                warning=(
                    "Live job search is temporarily unavailable. Showing "
                    "your last successful search results instead."
                ),
            )
        raise JobSearchError(
            "Could not reach the job search service right now. Try again "
            "shortly, or enter a job description manually (FR-05)."
        ) from exc

    results = [
        JobPostingResult(
            title=(item.get("title") or "Untitled role").strip(),
            company=((item.get("company") or {}).get("display_name") or "Unknown company").strip(),
            summary=_summarize(item.get("description") or ""),
            description=html.unescape(" ".join((item.get("description") or "").split())),
        )
        for item in payload.get("results", [])
    ]

    if not results:
        raise JobSearchError(
            f"No job postings matched '{keyword.strip()}'. Try a different "
            "keyword, or enter a job description manually (FR-05)."
        )

    _store_in_cache(cache, results)
    return JobSearchResponse(results=results, from_cache=False)
