"""Shared Flask extension instances.

Kept in their own module (rather than inside __init__.py) so any component
module can `from app.extensions import db` without triggering a circular
import with the application factory.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
