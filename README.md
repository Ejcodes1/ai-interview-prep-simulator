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
| WP-04 | LLM question-generation pipeline (FR-06–FR-08) | Stubbed |
| WP-05 | Answer capture (text + voice) & session UI (FR-09, FR-10) | Not started |
| WP-06 | Speech-to-text + LLM evaluation & scoring (FR-10–FR-13) | Stubbed |
| WP-07 | Feedback display, history & PDF export (FR-12, FR-14, FR-15) | Stubbed |

## Architecture

One module per component in the Component Diagram (Section 7.2, Figure 5):

```
app/
├── web/                 Web UI (Flask/Jinja + JS) — single entry point
├── ingestion/            Resume/JD Ingestion & Parser  — WP-02, implemented
├── job_search/           Job Search Module (Adzuna)     — WP-03, implemented
├── question_generator/   Question Generator (LLM)       — stub, WP-04
├── transcriber/          Speech-to-Text Transcriber      — stub, WP-06
├── answer_evaluator/     Answer Evaluator (LLM)          — stub, WP-06
├── feedback_engine/      Feedback & Scoring Engine       — stub, WP-07
├── report_generator/     PDF Report Generator            — stub, WP-07
└── session_store/        Session Store (SQLite/SQLAlchemy models)
```

The database schema in `app/session_store/models.py` implements the domain
model in Section 6 (Figure 3): `Candidate` → `InterviewSession` →
(`Resume`, `JobPosting`, `Question` → `Answer` → `Feedback`) →
`ReadinessReport`.

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

Then open http://127.0.0.1:5000/ and upload a resume + job description to
see the WP-02 ingestion pipeline (FR-01, FR-05, FR-06) in action.

## Test

```bash
pytest
```

## Notes

- `OPENAI_API_KEY` and `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` are wired into
  `app/config.py` and read from the environment (NFR-06: never exposed to
  the client), but aren't used yet — the modules that will call them
  (`job_search`, `question_generator`, `transcriber`, `answer_evaluator`)
  are stubs that raise `NotImplementedError` until their work packages land.
- The SQLite file lives at `instance/app.db` (gitignored) and is created
  automatically on first run, or explicitly via `flask init-db`.
