"""Command-line entry point for database migrations."""
from __future__ import annotations

import os
import sys

import click
from flask_migrate import Migrate, downgrade as _downgrade, upgrade as _upgrade

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app, db

app = create_app()
migrate = Migrate(app, db)


@click.group()
def cli() -> None:
    """Run database management commands."""


@cli.command("upgrade")
@click.argument("revision", required=False)
def upgrade_command(revision: str | None = None) -> None:
    """Apply database migrations up to ``revision``."""
    with app.app_context():
        target_revision = revision or "head"
        _upgrade(revision=target_revision)
        click.echo(f"Database upgraded to {target_revision}.")


@cli.command("downgrade")
@click.argument("revision", required=False)
def downgrade_command(revision: str | None = None) -> None:
    """Revert database migrations down to ``revision``."""
    with app.app_context():
        target_revision = revision or "-1"
        _downgrade(revision=target_revision)
        click.echo(f"Database downgraded to {target_revision}.")


if __name__ == "__main__":
    cli()
