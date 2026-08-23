"""Session Store component (Component Diagram, Figure 5).

Persists session state — candidate, resume, job posting, questions,
answers, feedback, and the final readiness report — in SQLite via
SQLAlchemy. Per the Component Diagram, the Question Generator reads from
and writes to this store (dashed arrow); other components produce data
that eventually flows through it once WP-04 onward wires them together.

Per NFR-03, nothing here is meant to outlive the active session in the
finished system — that cleanup policy is implemented alongside session
lifecycle handling in a later work package, not in this scaffold.
"""
