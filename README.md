# AI Interview Prep Simulator

An AI-driven system for personalized, job-posting-based interview practice.
See `docs/Phase1_Conception_Report.pdf` for the full Phase 1 conception
report (requirements, architecture, and planning this scaffold implements).

## Status

| Work Package | Description | Status |
|---|---|---|
| WP-01 | Requirements finalization & system design | Done (Phase 1 report) |
| WP-02 | Resume/JD ingestion & parser (FR-01, FR-05, FR-06) | **Implemented** |
| WP-03 | Job search API integration (FR-02–FR-04) | **Implemented** |
| WP-04 | LLM question-generation pipeline (FR-06–FR-08) | **Implemented** |
| WP-05 | Answer capture (text + voice) & session UI (FR-09, FR-10) | **Implemented** |
| WP-06 | Speech-to-text + LLM evaluation & scoring (FR-10–FR-13) | **Implemented** |
| WP-07 | Feedback display, history & PDF export (FR-12, FR-14, FR-15) | **Implemented** |
| WP-08 | Integration testing & bug fixing (FR-16, all NFRs) | In progress (unit + route tests cover each WP; no dedicated fault-injection pass yet) |
| WP-09 | Deployment & final documentation | **Implemented** — Dockerfile + docker-compose.yml, verified with a real `docker compose up` |

The full practice flow — upload resume → paste or search a job description
→ generate tailored questions → answer by typing or recording voice →
AI-scored per-question feedback → overall readiness score → PDF export —
now runs end to end.

**Known limitation (tracked for WP-08, per TR-05):** resumes, job
descriptions, and answers are currently persisted in SQLite with no
automatic cleanup after a session ends, which doesn't yet fully satisfy
NFR-03 ("not permanently stored beyond the active session"). No session
expiry/deletion mechanism is implemented yet.

## Architecture

One module per component in the Component Diagram (Section 7.2, Figure 5):

```
app/
├── web/                 Web UI (Flask/Jinja + JS) — single entry point
├── ingestion/            Resume/JD Ingestion & Parser  — WP-02, implemented
├── job_search/           Job Search Module (Adzuna)     — WP-03, implemented
├── question_generator/   Question Generator (LLM)       — WP-04, implemented
├── transcriber/          Speech-to-Text Transcriber      — WP-06, implemented
├── answer_evaluator/     Answer Evaluator (LLM)          — WP-06, implemented
├── feedback_engine/      Feedback & Scoring Engine       — WP-07, implemented
├── report_generator/     PDF Report Generator            — WP-07, implemented
└── session_store/        Session Store (SQLite/SQLAlchemy models)
```

The database schema in `app/session_store/models.py` implements the domain
model in Section 6 (Figure 3): `Candidate` → `InterviewSession` →
(`Resume`, `JobPosting`, `Question` → `Answer` → `Feedback`) →
`ReadinessReport`.

Per Figure 5 (Phase 1 report v4), three components read from and write to
the Session Store directly: the Question Generator (persists generated
questions), the Feedback & Scoring Engine (persists per-answer feedback,
then reads it all back to compute the aggregate score), and the PDF
Report Generator (reads the full session record, writes the exported
PDF's path back to `ReadinessReport.pdf_path`).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY / ADZUNA_APP_ID / ADZUNA_APP_KEY
```

## Run

```bash
python run.py
# or: flask --app run run --debug
```

Then open http://127.0.0.1:5050/ (macOS's AirPlay Receiver claims port
5000, so the dev server defaults to 5050 — override with the `PORT` env
var) and walk through the flow: upload a resume, provide a job description
(paste, upload, or search), start the interview, answer each question by
typing or recording voice, then review your scored feedback and export a
PDF.

Without a real `OPENAI_API_KEY`/`ADZUNA_APP_ID`/`ADZUNA_APP_KEY` in `.env`,
the app still runs — each integration shows a clear "not configured"
message and falls back to the manual-entry path instead of crashing
(FR-16, NFR-02).

## Run with Docker

```bash
cp .env.example .env   # then fill in real API keys
docker compose up --build
```

Serves the app at http://127.0.0.1:8000/. The SQLite database and
exported PDF reports persist in a named volume (`instance-data`) across
container restarts.

## Test

```bash
pytest
```

All external APIs (Adzuna, OpenAI chat completions, Whisper) are mocked
in tests, so the full suite runs offline without any real API keys.

## Notes

- API keys are read from the environment via `app/config.py`
  (NFR-06: never exposed to the client).
- LLM calls are capped per browser session via `MAX_LLM_CALLS_PER_SESSION`
  (NFR-07); exceeding it shows a clear message instead of failing silently.
- The SQLite file lives at `instance/app.db` (gitignored) and is created
  automatically on first run, or explicitly via `flask init-db`.
- Exported PDF reports are written to `instance/reports/` (gitignored).
