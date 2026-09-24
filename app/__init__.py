"""Application factory for the AI Interview Prep Simulator.

Wires together the components shown in the Component Diagram (Phase 1
report, Section 7.2 / Figure 5): the Web UI blueprint is registered here,
the Session Store's SQLAlchemy models are attached to the `db` extension,
and configuration (including the external API credentials used by the
stubbed modules) is loaded from `app.config`.
"""
from __future__ import annotations

import os

from flask import Flask

from .config import get_config
from .extensions import db


def create_app(config_name: str | None = None) -> Flask:
    # static_folder=None: there is no top-level app/static directory —
    # static assets live under the web blueprint (app/web/static) instead.
    # Leaving Flask's default app-level static route enabled would
    # otherwise claim the /static/... URL prefix first and shadow the
    # blueprint's own static route, which serves the CSS/JS that actually
    # exist.
    app = Flask(__name__, instance_relative_config=True, static_folder=None)
    app.config.from_object(get_config(config_name))

    os.makedirs(app.instance_path, exist_ok=True)

    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        db_path = os.path.join(app.instance_path, "app.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    db.init_app(app)

    # Session Store models must be imported (even though unused directly
    # here) so SQLAlchemy registers every table from the Section 6 domain
    # model before create_all() runs.
    from .session_store import models  # noqa: F401

    from .web.routes import web_bp

    app.register_blueprint(web_bp)

    # TEMPORARY — diagnosing a Render-only OpenAI connectivity failure.
    # Remove this and app/web/debug_routes.py before final submission.
    from .web.debug_routes import debug_bp

    app.register_blueprint(debug_bp)

    with app.app_context():
        if not app.config.get("TESTING"):
            db.create_all()

    _register_cli(app)

    return app


def _register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create all Session Store tables (see Section 6 domain model)."""
        with app.app_context():
            db.create_all()
        print(f"Initialized the database at {app.config['SQLALCHEMY_DATABASE_URI']}")
