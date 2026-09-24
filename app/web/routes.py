"""Web UI routes.

WP-02: a resume + job description upload form that calls the Resume/JD
Ingestion & Parser component and displays what it extracted.

WP-03: an alternative to pasting a job description — search real postings
via the Job Search Module and select one to auto-populate the same field
(FR-02-FR-04).

WP-04-WP-07: starting an interview session persists the ingested resume/JD
into the Session Store, generates tailored questions, and walks the
candidate through answering, scoring, and exporting a readiness report.
"""
from __future__ import annotations

import json
import os

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app.answer_evaluator import AnswerEvaluationError, evaluate_answer
from app.extensions import db
from app.feedback_engine import ScoringError, compute_overall_score, record_feedback
from app.ingestion import IngestionError, IngestionResult, ingest
from app.job_search import JobSearchError, search_job_postings
from app.question_generator import QuestionGenerationError, generate_questions
from app.report_generator import ReportGenerationError, generate_pdf_report
from app.session_store.models import Answer, InterviewSession, JobPosting, Question, Resume
from app.transcriber import TranscriptionError, transcribe_audio

web_bp = Blueprint(
    "web",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)


# --- NFR-07: cap LLM calls per (browser) session so usage cost is bounded --


class LlmBudgetExceededError(Exception):
    pass


def _use_llm_budget() -> None:
    limit = current_app.config.get("MAX_LLM_CALLS_PER_SESSION", 20)
    used = session.get("llm_call_count", 0)
    if used >= limit:
        raise LlmBudgetExceededError(
            f"This browser session has reached its limit of {limit} AI calls. "
            "Start a new session to continue."
        )
    session["llm_call_count"] = used + 1


def _get_session_or_404(session_uuid: str) -> InterviewSession:
    interview_session = InterviewSession.query.filter_by(session_uuid=session_uuid).first()
    if interview_session is None:
        abort(404)
    return interview_session


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

    resume_filename = resume_file.filename

    try:
        result = ingest(
            resume_file,
            job_description_text=job_description_text,
            job_description_file=job_description_file,
        )
    except IngestionError as exc:
        return render_template("index.html", error=str(exc)), 400

    return render_template(
        "ingestion_result.html", result=result, resume_filename=resume_filename
    )


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


# --- WP-04: start an interview session (persist + generate questions) ------


@web_bp.post("/interview/start")
def interview_start_view():
    resume_text = request.form.get("resume_text", "")
    job_description_text = request.form.get("job_description_text", "")
    skills = request.form.getlist("skills")
    role = request.form.get("role", "") or "Untitled role"
    resume_filename = request.form.get("resume_filename", "") or "resume"

    fallback_result = IngestionResult(
        resume_text=resume_text,
        job_description_text=job_description_text,
        skills=skills,
        role=role or None,
    )

    try:
        _use_llm_budget()
        drafts = generate_questions(resume_text, job_description_text, skills)
    except (QuestionGenerationError, LlmBudgetExceededError) as exc:
        return render_template(
            "ingestion_result.html",
            result=fallback_result,
            resume_filename=resume_filename,
            error=str(exc),
        ), 400

    resume = Resume(
        file_name=resume_filename,
        extracted_text=resume_text,
        extracted_skills=json.dumps(skills),
    )
    job_posting = JobPosting(title=role, description=job_description_text, source="manual")
    interview_session = InterviewSession(resume=resume, job_posting=job_posting, status="in_progress")
    db.session.add(interview_session)

    for draft in drafts:
        db.session.add(
            Question(
                session=interview_session,
                text=draft.text,
                type=draft.type,
                order_index=draft.order_index,
            )
        )
    db.session.commit()

    return redirect(url_for("web.interview_view", session_uuid=interview_session.session_uuid))


# --- WP-05: one-question-at-a-time session flow, typed answer capture ------


@web_bp.get("/interview/<session_uuid>")
def interview_view(session_uuid: str):
    interview_session = _get_session_or_404(session_uuid)

    next_question = next(
        (q for q in interview_session.questions if q.answer is None), None
    )
    if next_question is None:
        return redirect(url_for("web.interview_summary_view", session_uuid=session_uuid))

    total = len(interview_session.questions)
    answered = total - sum(1 for q in interview_session.questions if q.answer is None)

    return render_template(
        "interview_question.html",
        session=interview_session,
        question=next_question,
        answered=answered,
        total=total,
    )


@web_bp.post("/interview/<session_uuid>/transcribe")
def interview_transcribe_view(session_uuid: str):
    """FR-10: transcribe a recorded voice answer; the client fills the
    typed-answer textarea with the result so the candidate can confirm or
    edit it (TR-02 mitigation) before submitting via the normal answer
    route — voice input never bypasses that review step.
    """
    _get_session_or_404(session_uuid)

    audio_file = request.files.get("audio")

    try:
        _use_llm_budget()
        transcript = transcribe_audio(audio_file)
    except (TranscriptionError, LlmBudgetExceededError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"transcript": transcript})


@web_bp.post("/interview/<session_uuid>/answer")
def interview_answer_view(session_uuid: str):
    interview_session = _get_session_or_404(session_uuid)

    question_id = request.form.get("question_id", type=int)
    answer_text = request.form.get("answer_text", "")

    question = next(
        (q for q in interview_session.questions if q.id == question_id), None
    )
    if question is None:
        abort(404)
    if question.answer is not None:
        return redirect(url_for("web.interview_view", session_uuid=session_uuid))

    total = len(interview_session.questions)
    answered = total - sum(1 for q in interview_session.questions if q.answer is None)

    if not answer_text.strip():
        return render_template(
            "interview_question.html",
            session=interview_session,
            question=question,
            answered=answered,
            total=total,
            error="Please type an answer before submitting.",
        ), 400

    try:
        _use_llm_budget()
        evaluation = evaluate_answer(question.text, answer_text)
    except (AnswerEvaluationError, LlmBudgetExceededError) as exc:
        return render_template(
            "interview_question.html",
            session=interview_session,
            question=question,
            answered=answered,
            total=total,
            error=str(exc),
            prefill_answer=answer_text,
        ), 400

    answer = Answer(question=question, text=answer_text, input_mode="text")
    db.session.add(answer)
    db.session.commit()

    record_feedback(answer, evaluation)

    if all(q.answer is not None for q in interview_session.questions):
        compute_overall_score(interview_session)
        return redirect(url_for("web.interview_summary_view", session_uuid=session_uuid))

    return redirect(url_for("web.interview_view", session_uuid=session_uuid))


# --- WP-07: full session review, overall score, PDF export -----------------


@web_bp.get("/interview/<session_uuid>/summary")
def interview_summary_view(session_uuid: str):
    interview_session = _get_session_or_404(session_uuid)

    if interview_session.readiness_report is None:
        return redirect(url_for("web.interview_view", session_uuid=session_uuid))

    return render_template("interview_summary.html", session=interview_session)


@web_bp.get("/interview/<session_uuid>/report.pdf")
def interview_report_view(session_uuid: str):
    interview_session = _get_session_or_404(session_uuid)

    try:
        output_dir = os.path.join(current_app.instance_path, "reports")
        pdf_path = generate_pdf_report(interview_session, output_dir)
    except ReportGenerationError as exc:
        return render_template(
            "interview_summary.html", session=interview_session, error=str(exc)
        ), 400

    return send_file(
        pdf_path, as_attachment=True, download_name=f"readiness_report_{session_uuid}.pdf"
    )
