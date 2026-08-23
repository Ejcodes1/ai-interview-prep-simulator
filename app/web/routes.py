"""Web UI routes.

WP-02: a resume + job description upload form that calls the Resume/JD
Ingestion & Parser component and displays what it extracted.

WP-03: an alternative to pasting a job description — search real postings
via the Job Search Module and select one to auto-populate the same field
(FR-02-FR-04).

Answer capture, evaluation, and PDF export are wired in as later work
packages replace their stub modules.
"""
from __future__ import annotations

from flask import Blueprint, current_app, render_template, request, session

from app.ingestion import IngestionError, ingest
from app.job_search import JobSearchError, search_job_postings

web_bp = Blueprint(
    "web",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)


@web_bp.get("/")
def index():
    return render_template("index.html")


@web_bp.post("/ingest")
def ingest_view():
    resume_file = request.files.get("resume")
    job_description_text = request.form.get("job_description", "")
    job_description_file = request.files.get("job_description_file")
    # An empty file input still arrives as a FileStorage with filename == "".
    if job_description_file is not None and not job_description_file.filename:
        job_description_file = None

    if resume_file is None or not resume_file.filename:
        return render_template(
            "index.html",
            error="Please choose a resume file (PDF or DOCX) to upload.",
        ), 400

    try:
        result = ingest(
            resume_file,
            job_description_text=job_description_text,
            job_description_file=job_description_file,
        )
    except IngestionError as exc:
        return render_template("index.html", error=str(exc)), 400

    return render_template("ingestion_result.html", result=result)


@web_bp.get("/jobs/search")
def job_search_form():
    return render_template("job_search_form.html")


@web_bp.post("/jobs/search")
def job_search_view():
    keyword = request.form.get("keyword", "")
    location = request.form.get("location", "")

    try:
        response = search_job_postings(
            keyword,
            location,
            country=current_app.config.get("ADZUNA_COUNTRY"),
            # A dict-like cache (Flask's session) lets the TR-03 fallback
            # reuse the last successful results if a later search fails.
            cache=session,
        )
    except JobSearchError as exc:
        return render_template(
            "job_search_form.html", error=str(exc), keyword=keyword, location=location
        ), 400

    return render_template(
        "job_search_results.html",
        results=response.results,
        warning=response.warning,
        keyword=keyword,
    )


@web_bp.post("/jobs/select")
def job_select_view():
    """FR-04: populate the job description field from a selected posting.

    Renders the index form directly (rather than redirecting through a
    stored session value) so the full posting text never has to round-trip
    through a cookie.
    """
    title = request.form.get("title", "")
    company = request.form.get("company", "")
    description = request.form.get("description", "")

    return render_template(
        "index.html",
        prefill_job_title=title,
        prefill_job_company=company,
        prefill_job_description=description,
    )
