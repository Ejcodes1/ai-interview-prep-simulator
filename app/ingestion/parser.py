"""Resume / JD Ingestion & Parser component (WP-02).

Implements:

    FR-01: accept a resume upload in PDF or DOCX format and extract its text.
    FR-05: accept a job description as manually pasted text OR an uploaded
           file, as an alternative to the Job Search Module (FR-02-FR-04).
    FR-06: extract at least 5 key role/skill terms from the combined
           resume + job-description text.

Design notes
------------
FR-06 extraction is intentionally rule-based (a curated lexicon plus a
frequency-based fallback), not LLM-based: the LLM integration is scoped to
question generation and answer evaluation (WP-04/WP-06), and keeping this
component's output deterministic makes it fast, free to run, and easy to
unit test without any API key.

Any file-like object with a `.filename` attribute and a `.read()` method
(e.g. a Werkzeug/Flask `FileStorage`) is accepted, so these functions work
both behind a real upload route and with plain in-memory fixtures in tests.
"""
from __future__ import annotations

import io
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass, field

from .skills_lexicon import SKILLS_LEXICON

RESUME_EXTENSIONS = {".pdf", ".docx"}
JOB_DESCRIPTION_EXTENSIONS = {".pdf", ".docx", ".txt"}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "of", "to",
    "in", "on", "at", "for", "with", "by", "as", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "these", "those", "it", "its",
    "we", "you", "your", "our", "i", "they", "he", "she", "will", "shall",
    "job", "role", "position", "title", "company", "team", "work",
    "experience", "years", "year", "responsibilities", "requirements",
    "about", "must", "have", "who", "what", "when", "where", "resume",
}


class IngestionError(Exception):
    """Raised for any resume/JD input problem the user must fix (FR-16)."""


@dataclass
class IngestionResult:
    resume_text: str
    job_description_text: str
    skills: list[str] = field(default_factory=list)
    role: str | None = None


def _read_file_storage(file_storage) -> tuple[str, bytes]:
    """Extract (filename, raw bytes) from a Flask/Werkzeug FileStorage-like
    object, tolerating plain file-like objects used in tests."""
    filename = getattr(file_storage, "filename", None) or ""
    stream = getattr(file_storage, "stream", None)
    try:
        data = file_storage.read()
    except AttributeError as exc:
        raise IngestionError("No file was provided.") from exc
    finally:
        # Reset so the caller (or Flask) can still access/save the file
        # afterwards if needed.
        seek_target = stream if stream is not None else file_storage
        if hasattr(seek_target, "seek"):
            try:
                seek_target.seek(0)
            except (OSError, ValueError):
                pass
    return filename, data


def _extension(filename: str) -> str:
    idx = filename.rfind(".")
    return filename[idx:].lower() if idx != -1 else ""


def _extract_pdf_text(data: bytes) -> str:
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:  # pdfplumber/pdfminer raise various exceptions
        raise IngestionError(
            "The uploaded PDF could not be read. It may be corrupted, "
            "password-protected, or not a valid PDF file."
        ) from exc
    return "\n".join(pages_text).strip()


def _extract_docx_text(data: bytes) -> str:
    import docx

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:  # python-docx raises PackageNotFoundError et al.
        raise IngestionError(
            "The uploaded DOCX file could not be read. It may be corrupted "
            "or not a valid Word document."
        ) from exc
    return "\n".join(p.text for p in document.paragraphs).strip()


def _extract_text_by_extension(filename: str, data: bytes, allowed: set[str]) -> str:
    if not filename:
        raise IngestionError("No file was provided.")

    ext = _extension(filename)
    if ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise IngestionError(
            f"Unsupported file type '{ext or filename}'. "
            f"Please upload one of: {allowed_list}."
        )

    if not data:
        raise IngestionError(f"The uploaded file '{filename}' is empty.")

    if ext == ".pdf":
        text = _extract_pdf_text(data)
    elif ext == ".docx":
        text = _extract_docx_text(data)
    else:  # ".txt"
        try:
            text = data.decode("utf-8").strip()
        except UnicodeDecodeError as exc:
            raise IngestionError(
                f"The uploaded file '{filename}' is not valid UTF-8 text."
            ) from exc

    if not text:
        raise IngestionError(
            f"No readable text could be extracted from '{filename}'."
        )
    return text


def extract_resume_text(file_storage) -> str:
    """FR-01: extract text from an uploaded PDF or DOCX resume."""
    filename, data = _read_file_storage(file_storage)
    return _extract_text_by_extension(filename, data, RESUME_EXTENSIONS)


def extract_job_description_text(text: str | None = None, file_storage=None) -> str:
    """FR-05: accept a job description as pasted text or an uploaded file."""
    if text and text.strip():
        return text.strip()

    if file_storage is not None:
        filename, data = _read_file_storage(file_storage)
        if filename:
            return _extract_text_by_extension(
                filename, data, JOB_DESCRIPTION_EXTENSIONS
            )

    raise IngestionError(
        "Please paste a job description or upload a job description file."
    )


def extract_skills(combined_text: str, min_skills: int = 5) -> list[str]:
    """FR-06: extract at least `min_skills` key role/skill terms.

    Matching happens in two passes:

    1. Lexicon match — case-insensitive whole-phrase search against
       `SKILLS_LEXICON`, ordered by first appearance in the text.
    2. Frequency fallback — if fewer than `min_skills` lexicon terms were
       found, the most frequent capitalized proper-noun-like tokens (e.g.
       tool/technology names not in the lexicon) are added until the
       minimum is reached, or the text is exhausted.
    """
    if not combined_text or not combined_text.strip():
        return []

    found: "OrderedDict[str, None]" = OrderedDict()
    lowered = combined_text.lower()
    for skill in SKILLS_LEXICON:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, lowered):
            found[skill] = None

    if len(found) < min_skills:
        candidates = re.findall(r"\b[A-Z][A-Za-z0-9+.#]{1,}\b", combined_text)
        counts = Counter(
            token for token in candidates if token.lower() not in _STOPWORDS
        )
        for token, _count in counts.most_common():
            if len(found) >= min_skills:
                break
            if token not in found:
                found[token] = None

    return list(found.keys())


_ROLE_LABEL_PATTERN = re.compile(
    r"(?:job title|position|role)\s*[:\-]\s*(?P<role>.+)", re.IGNORECASE
)


def extract_role(job_description_text: str) -> str | None:
    """Best-effort extraction of the job title/role from JD text.

    Looks for an explicit "Job Title:"/"Position:"/"Role:" label first;
    falls back to the first short, non-sentence-like line (e.g. a heading
    such as "Backend Software Engineer" at the top of a posting).
    """
    if not job_description_text:
        return None

    for line in job_description_text.splitlines()[:10]:
        match = _ROLE_LABEL_PATTERN.search(line)
        if match:
            role = match.group("role").strip()
            if role:
                return role

    for line in job_description_text.splitlines():
        candidate = line.strip()
        if candidate and len(candidate) <= 80 and not candidate.endswith("."):
            return candidate

    return None


def ingest(
    resume_file,
    job_description_text: str | None = None,
    job_description_file=None,
) -> IngestionResult:
    """Run the full WP-02 pipeline: FR-01 + FR-05 + FR-06.

    Raises IngestionError with a user-facing message on any invalid input
    (FR-16), and never lets a parsing library's raw exception escape.
    """
    resume_text = extract_resume_text(resume_file)
    jd_text = extract_job_description_text(
        text=job_description_text, file_storage=job_description_file
    )
    combined_text = f"{resume_text}\n{jd_text}"
    skills = extract_skills(combined_text)
    role = extract_role(jd_text)

    return IngestionResult(
        resume_text=resume_text,
        job_description_text=jd_text,
        skills=skills,
        role=role,
    )
