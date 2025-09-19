"""Utility for creating the first administrator account.

The script is intentionally small so that operators can seed an initial admin
user in a fresh deployment.  Credentials are provided via command-line
arguments or environment variables to avoid hard-coded defaults.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from typing import Sequence

from app import create_app, db
from models import User

USERNAME_ENV = "ADMIN_USERNAME"
EMAIL_ENV = "ADMIN_EMAIL"
PASSWORD_ENV = "ADMIN_PASSWORD"


def _resolve_credentials(argv: Sequence[str] | None = None) -> tuple[str, str, str]:
    """Return username, email, and password supplied via CLI/env variables."""

    parser = argparse.ArgumentParser(description="Create the first admin user")
    parser.add_argument("--username", help=f"Admin username or set {USERNAME_ENV}")
    parser.add_argument("--email", help=f"Admin email or set {EMAIL_ENV}")
    parser.add_argument(
        "--password",
        help=(
            "Admin password or set {env}. If omitted and running in a TTY, "
            "you will be prompted."
        ).format(env=PASSWORD_ENV),
    )

    args = parser.parse_args(argv)

    username = args.username or os.getenv(USERNAME_ENV)
    if not username:
        parser.error(
            f"Username is required. Provide --username or set {USERNAME_ENV}."
        )

    email = args.email or os.getenv(EMAIL_ENV)
    if not email:
        parser.error(f"Email is required. Provide --email or set {EMAIL_ENV}.")

    password = args.password or os.getenv(PASSWORD_ENV)
    if not password:
        if sys.stdin is not None and sys.stdin.isatty():
            password = getpass.getpass("Admin password: ")
        else:
            parser.error(
                "Password is required. Provide --password or set "
                f"{PASSWORD_ENV}."
            )

    return username, email, password


def _validate_password(password: str) -> None:
    """Ensure the supplied password meets a basic security policy."""

    errors = []
    if len(password) < 12:
        errors.append("at least 12 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("a lowercase letter")
    if not re.search(r"\d", password):
        errors.append("a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("a symbol")

    if errors:
        raise ValueError(
            "Password is too weak; include " + ", ".join(errors) + "."
        )


def create_admin_user(username: str, email: str, password: str) -> bool:
    """Create an administrator account when one does not already exist.

    Returns ``True`` when a new admin was created and ``False`` if the
    email address is already registered.
    """

    _validate_password(password)

    existing = User.query.filter_by(email=email).first()
    if existing:
        print(f"Admin with email '{email}' already exists; no action taken.")
        return False

    username_conflict = User.query.filter_by(username=username).first()
    if username_conflict:
        raise ValueError(
            f"Username '{username}' is already in use. Choose a different username."
        )

    admin = User(username=username, email=email, is_admin=True)
    admin.set_password(password)

    db.session.add(admin)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    print("Admin user created successfully")
    return True


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point used by the CLI and automated tests."""

    try:
        username, email, password = _resolve_credentials(argv)
    except SystemExit:
        # argparse.error already printed a message; propagate exit code.
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Error resolving credentials: {exc}")
        return 1

    app = create_app()
    with app.app_context():
        try:
            create_admin_user(username, email, password)
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1
        except Exception as exc:  # pragma: no cover - unexpected failure
            print(f"Error creating admin user: {exc}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
