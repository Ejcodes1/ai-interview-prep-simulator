"""Web UI routes.

WP-02 scope: a single upload form (resume + job description) that calls the
Resume/JD Ingestion & Parser component and displays what it extracted.
Job search, question generation, answer capture, evaluation, and PDF export
are wired in as later work packages replace their stub modules.
"""
from __future__ import annotations

from flask import Blueprint, render_template, request

from app.ingestion import IngestionError, ingest

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
