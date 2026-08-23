"""SQLAlchemy models implementing the Section 6 domain model (Figure 3).

Entities and cardinalities, straight from the domain model:

    Candidate       1 --- *  InterviewSession
    InterviewSession 1 --- 1 JobPosting
    InterviewSession 1 --- 1 Resume
    InterviewSession 1 --- *  Question
    Question        1 --- 1  Answer
    Answer          1 --- 1  Feedback
    InterviewSession 1 --- 1 ReadinessReport

A Candidate has no login/auth (the project excludes persistent accounts),
so `candidate_id` on InterviewSession is nullable — a session can exist
for an anonymous candidate who never supplied contact details.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(320), nullable=True)
    contact_info = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    sessions = db.relationship(
        "InterviewSession", back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"<Candidate id={self.id} name={self.name!r}>"


class JobPosting(db.Model):
    __tablename__ = "job_postings"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    company = db.Column(db.String(300), nullable=True)
    description = db.Column(db.Text, nullable=False)
    # Where the posting came from: "manual", "adzuna", or "the_muse".
    source = db.Column(db.String(50), nullable=False, default="manual")
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    session = db.relationship(
        "InterviewSession", back_populates="job_posting", uselist=False
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<JobPosting id={self.id} title={self.title!r}>"


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(300), nullable=False)
    extracted_text = db.Column(db.Text, nullable=False)
    # Stored as a JSON-encoded list of strings (see ingestion.parser).
    extracted_skills = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    session = db.relationship("InterviewSession", back_populates="resume", uselist=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resume id={self.id} file_name={self.file_name!r}>"


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"

    id = db.Column(db.Integer, primary_key=True)
    # Public-facing identifier (Figure 3: InterviewSession.sessionId).
    session_uuid = db.Column(
        db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    status = db.Column(db.String(30), nullable=False, default="created")
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=True)
    resume_id = db.Column(
        db.Integer, db.ForeignKey("resumes.id"), unique=True, nullable=True
    )
    job_posting_id = db.Column(
        db.Integer, db.ForeignKey("job_postings.id"), unique=True, nullable=True
    )

    candidate = db.relationship("Candidate", back_populates="sessions")
    resume = db.relationship("Resume", back_populates="session")
    job_posting = db.relationship("JobPosting", back_populates="session")
    questions = db.relationship(
        "Question",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Question.order_index",
    )
    readiness_report = db.relationship(
        "ReadinessReport",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InterviewSession id={self.id} status={self.status!r}>"


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("interview_sessions.id"), nullable=False
    )
    text = db.Column(db.Text, nullable=False)
    # "behavioral" or "technical" (Section 6 / Glossary).
    type = db.Column(db.String(20), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    session = db.relationship("InterviewSession", back_populates="questions")
    answer = db.relationship(
        "Answer", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Question id={self.id} type={self.type!r}>"


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id"), unique=True, nullable=False
    )
    text = db.Column(db.Text, nullable=False)
    # "text" or "voice".
    input_mode = db.Column(db.String(10), nullable=False, default="text")
    # Populated by the Speech-to-Text Transcriber when input_mode == "voice".
    transcript = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    question = db.relationship("Question", back_populates="answer")
    feedback = db.relationship(
        "Feedback", back_populates="answer", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Answer id={self.id} input_mode={self.input_mode!r}>"


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(
        db.Integer, db.ForeignKey("answers.id"), unique=True, nullable=False
    )
    score = db.Column(db.Float, nullable=False)
    strengths = db.Column(db.Text, nullable=True)
    weaknesses = db.Column(db.Text, nullable=True)
    suggestions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)

    answer = db.relationship("Answer", back_populates="feedback")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Feedback id={self.id} score={self.score}>"


class ReadinessReport(db.Model):
    __tablename__ = "readiness_reports"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("interview_sessions.id"), unique=True, nullable=False
    )
    overall_score = db.Column(db.Float, nullable=False)
    generated_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    pdf_path = db.Column(db.String(500), nullable=True)

    session = db.relationship("InterviewSession", back_populates="readiness_report")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ReadinessReport id={self.id} overall_score={self.overall_score}>"
