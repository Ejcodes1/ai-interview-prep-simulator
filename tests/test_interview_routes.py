"""Integration tests for the interview session Web UI routes (WP-04–WP-07).

The LLM calls (question generation, answer evaluation) are mocked at the
route boundary — app.web.routes imports generate_questions/evaluate_answer
by name, so monkeypatching those names here is equivalent to monkeypatching
the OpenAI client itself, without needing a real API key.
"""
from __future__ import annotations

from app.web import routes as web_routes
from app.answer_evaluator import EvaluationResult
from app.question_generator import QuestionDraft
from app.session_store.models import InterviewSession


def _fake_questions(*_args, **_kwargs):
    return [
        QuestionDraft(text="Tell me about a bug you fixed.", type="behavioral", order_index=0),
        QuestionDraft(text="How would you index a slow query?", type="technical", order_index=1),
        QuestionDraft(text="Describe a team conflict you resolved.", type="behavioral", order_index=2),
    ]


def _fake_evaluation(*_args, **_kwargs):
    return EvaluationResult(score=80, strengths="Good example.", weaknesses="", suggestions="Add a metric.")


def _start_session(client, monkeypatch, sample_resume_filename):
    monkeypatch.setattr(web_routes, "generate_questions", _fake_questions)
    response = client.post(
        "/interview/start",
        data={
            "resume_text": "Jane Doe resume text",
            "job_description_text": "Junior Backend Developer JD text",
            "role": "Junior Backend Developer",
            "resume_filename": sample_resume_filename,
            "skills": ["Python", "Flask", "SQL"],
        },
        follow_redirects=True,
    )
    return response


def test_interview_start_generates_questions_and_shows_first_one(
    client, monkeypatch, sample_resume_filename
):
    response = _start_session(client, monkeypatch, sample_resume_filename)

    assert response.status_code == 200
    body = response.data.decode()
    assert "Question 1 of 3" in body
    assert "Tell me about a bug you fixed." in body


def test_interview_start_shows_clear_error_on_generation_failure(client, monkeypatch):
    from app.question_generator import QuestionGenerationError

    def _raise(*_a, **_k):
        raise QuestionGenerationError("The question-generation service is temporarily unavailable.")

    monkeypatch.setattr(web_routes, "generate_questions", _raise)

    response = client.post(
        "/interview/start",
        data={
            "resume_text": "resume text",
            "job_description_text": "jd text",
            "role": "Engineer",
            "skills": ["Python"],
        },
    )

    assert response.status_code == 400
    assert b"temporarily unavailable" in response.data


def test_interview_answer_flow_progresses_to_summary_with_overall_score(
    app, client, monkeypatch, sample_resume_filename
):
    _start_session(client, monkeypatch, sample_resume_filename)
    monkeypatch.setattr(web_routes, "evaluate_answer", _fake_evaluation)

    with app.app_context():
        session_uuid = InterviewSession.query.first().session_uuid

    for _ in range(3):
        page = client.get(f"/interview/{session_uuid}")
        # extract the question_id from the hidden input in the rendered form
        body = page.data.decode()
        marker = 'name="question_id" value="'
        start = body.index(marker) + len(marker)
        question_id = body[start:body.index('"', start)]

        response = client.post(
            f"/interview/{session_uuid}/answer",
            data={"question_id": question_id, "answer_text": "A thoughtful, concrete answer."},
            follow_redirects=True,
        )

    assert response.status_code == 200
    body = response.data.decode()
    assert "Overall readiness score" in body
    assert "80" in body


def test_interview_answer_rejects_blank_answer(app, client, monkeypatch, sample_resume_filename):
    _start_session(client, monkeypatch, sample_resume_filename)

    with app.app_context():
        session_uuid = InterviewSession.query.first().session_uuid
        question_id = InterviewSession.query.first().questions[0].id

    response = client.post(
        f"/interview/{session_uuid}/answer",
        data={"question_id": question_id, "answer_text": "   "},
    )

    assert response.status_code == 400
    assert b"Please type an answer" in response.data


def test_interview_answer_shows_clear_error_on_evaluation_failure_and_does_not_persist(
    app, client, monkeypatch, sample_resume_filename
):
    """NFR-02 fault injection: the Answer Evaluator (an external API call)
    fails mid-flow — the candidate must see a clear message, not a crash,
    and the unscored answer must not be silently recorded as answered."""
    from app.answer_evaluator import AnswerEvaluationError

    _start_session(client, monkeypatch, sample_resume_filename)

    def _raise(*_a, **_k):
        raise AnswerEvaluationError(
            "The answer-evaluation service is temporarily unavailable. "
            "Please try again shortly."
        )

    monkeypatch.setattr(web_routes, "evaluate_answer", _raise)

    with app.app_context():
        session_uuid = InterviewSession.query.first().session_uuid
        question_id = InterviewSession.query.first().questions[0].id

    response = client.post(
        f"/interview/{session_uuid}/answer",
        data={"question_id": question_id, "answer_text": "A thoughtful answer."},
    )

    assert response.status_code == 400
    assert b"temporarily unavailable" in response.data

    with app.app_context():
        question = InterviewSession.query.first().questions[0]
        assert question.answer is None  # not persisted — retry is still possible


def test_interview_summary_redirects_if_session_incomplete(
    app, client, monkeypatch, sample_resume_filename
):
    _start_session(client, monkeypatch, sample_resume_filename)

    with app.app_context():
        session_uuid = InterviewSession.query.first().session_uuid

    response = client.get(f"/interview/{session_uuid}/summary", follow_redirects=True)

    assert response.status_code == 200
    assert b"Question 1 of 3" in response.data


def test_interview_transcribe_returns_transcript_json(
    app, client, monkeypatch, sample_resume_filename
):
    import io

    _start_session(client, monkeypatch, sample_resume_filename)
    monkeypatch.setattr(
        web_routes, "transcribe_audio", lambda *_a, **_k: "A transcribed answer."
    )

    with app.app_context():
        session_uuid = InterviewSession.query.first().session_uuid

    response = client.post(
        f"/interview/{session_uuid}/transcribe",
        data={"audio": (io.BytesIO(b"fake-audio"), "answer.webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json() == {"transcript": "A transcribed answer."}


def test_interview_transcribe_returns_clear_error_on_failure(
    app, client, monkeypatch, sample_resume_filename
):
    import io

    from app.transcriber import TranscriptionError

    _start_session(client, monkeypatch, sample_resume_filename)

    def _raise(*_a, **_k):
        raise TranscriptionError("No speech could be transcribed from the recording.")

    monkeypatch.setattr(web_routes, "transcribe_audio", _raise)

    with app.app_context():
        session_uuid = InterviewSession.query.first().session_uuid

    response = client.post(
        f"/interview/{session_uuid}/transcribe",
        data={"audio": (io.BytesIO(b"fake-audio"), "answer.webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "No speech" in response.get_json()["error"]


def test_interview_report_pdf_downloads_after_completion(
    app, client, monkeypatch, sample_resume_filename, tmp_path
):
    app.instance_path = str(tmp_path)

    _start_session(client, monkeypatch, sample_resume_filename)
    monkeypatch.setattr(web_routes, "evaluate_answer", _fake_evaluation)

    with app.app_context():
        session_uuid = InterviewSession.query.first().session_uuid

    for _ in range(3):
        page = client.get(f"/interview/{session_uuid}")
        body = page.data.decode()
        marker = 'name="question_id" value="'
        start = body.index(marker) + len(marker)
        question_id = body[start:body.index('"', start)]
        client.post(
            f"/interview/{session_uuid}/answer",
            data={"question_id": question_id, "answer_text": "A thoughtful, concrete answer."},
        )

    response = client.get(f"/interview/{session_uuid}/report.pdf")

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert len(response.data) > 0
