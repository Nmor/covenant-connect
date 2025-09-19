"""Utility script to ensure the database schema is up to date."""
from __future__ import annotations

import os
import sys

from flask_migrate import Migrate, upgrade

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db


def init_db() -> None:
    """Apply migrations so the database schema matches the models."""
    app = create_app()
    Migrate(app, db)
    with app.app_context():
        upgrade()
        print("Database schema upgraded successfully!")


if __name__ == "__main__":
    init_db()
