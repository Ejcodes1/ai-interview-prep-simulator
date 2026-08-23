"""Application configuration.

Reads secrets/credentials from environment variables (NFR-06: API keys are
stored server-side only, never exposed to the client). Values are loaded from
a local .env file via python-dotenv if present — see .env.example for the
full list of supported variables.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """Settings shared by every environment."""

    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 10 MB cap on any single upload (resume, JD file, or audio recording).
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # --- External API credentials (WP-03, WP-04, WP-06) ---
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
    ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
    ADZUNA_COUNTRY = os.environ.get("ADZUNA_COUNTRY", "us")

    # NFR-07: cap LLM calls per session to bound usage cost.
    MAX_LLM_CALLS_PER_SESSION = int(os.environ.get("MAX_LLM_CALLS_PER_SESSION", 20))

    # Explicit override for the SQLite URI; if unset, create_app() falls back
    # to a file inside the Flask instance folder.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    # Fast, isolated, in-memory DB for the test suite.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG = False


_CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    """Resolve a config class by name, falling back to FLASK_ENV then dev."""
    name = name or os.environ.get("FLASK_ENV", "development")
    return _CONFIGS.get(name, DevelopmentConfig)
