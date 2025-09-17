from __future__ import annotations

from typing import Any, Iterable

from flask import current_app

from app import create_app
from models import PrayerRequest


def send_prayer_notification(prayer_request_id: int) -> None:
    """Log that a prayer request should notify admins."""

    app = create_app()
    with app.app_context():
        prayer = PrayerRequest.query.get(prayer_request_id)
        if prayer is None:
            current_app.logger.warning(
                'Prayer request %s not found for notification.', prayer_request_id
            )
            return
        current_app.logger.info('Prayer request %s ready for notification.', prayer.id)


def trigger_automation(trigger: str, context: dict[str, Any] | None = None) -> int:
    """Stub automation hook that always reports no matching automations."""

    context = context or {}
    current_app.logger.debug('Automation trigger %s received with %s', trigger, context)
    return 0


def run_automations_for_ids(
    automation_ids: Iterable[int],
    context: dict[str, Any] | None = None,
    trigger: str | None = None,
) -> None:
    """Compatibility shim for previous tasks module."""

    current_app.logger.debug(
        'Automation execution skipped for ids=%s trigger=%s context=%s',
        list(automation_ids),
        trigger,
        context,
    )


def schedule_kpi_digest(period: str = '7d', recipients: Iterable[str] | None = None) -> None:
    """Compatibility shim for previous tasks module."""

    current_app.logger.debug(
        'KPI digest scheduling skipped for period=%s recipients=%s',
        period,
        list(recipients) if recipients else None,
    )


def send_kpi_digest(period: str = '7d', recipients: Iterable[str] | None = None) -> None:
    """Compatibility shim for previous tasks module."""

    current_app.logger.debug(
        'KPI digest email skipped for period=%s recipients=%s',
        period,
        list(recipients) if recipients else None,
    )
