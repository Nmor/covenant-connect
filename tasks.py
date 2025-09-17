"""Utility functions for asynchronous tasks and workflow automations."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional

from flask import current_app, render_template_string
from flask_mail import Message

from models import (
    Automation,
    AutomationStep,
    Event,
    PrayerRequest,
    Sermon,
    User,
)
from routes.admin_reports import build_kpi_digest, resolve_reporting_window


def send_prayer_notification(prayer_request_id: int) -> None:
    from app import create_app, mail

    """Background task to send prayer notification emails to admins."""
    app = create_app()
    with app.app_context():
        prayer_request = PrayerRequest.query.get(prayer_request_id)
        if not prayer_request:
            current_app.logger.error("Prayer request not found")
            return

        admin_users = User.query.filter_by(is_admin=True).all()
        if not admin_users:
            current_app.logger.warning(
                "No admin users found to notify about prayer request"
            )
            return

        subject = "New Prayer Request Received"
        body = f"""
A new prayer request has been submitted:

From: {prayer_request.name}
Email: {prayer_request.email}
Request: {prayer_request.request}
Public: {'Yes' if prayer_request.is_public else 'No'}
Submitted: {prayer_request.created_at.strftime('%B %d, %Y %I:%M %p')}
"""
        msg = Message(
            subject=subject,
            recipients=[admin.email for admin in admin_users],
            body=body,
        )
        mail.send(msg)
        current_app.logger.info(
            "Prayer request notification sent to %s admin(s)",
            len(admin_users),
        )


def _determine_digest_recipients() -> List[str]:
    recipients: List[str] = []
    candidate_users = User.query.filter(User.email.isnot(None)).all()
    for user in candidate_users:
        preferences = user.notification_preferences or {}
        role = (preferences.get('role') or '').lower()
        wants_digest = preferences.get('receive_kpi_digest', True)
        if user.is_admin or role in {'department_head', 'executive'}:
            if wants_digest and user.email:
                recipients.append(user.email)
    return recipients


def send_kpi_digest(period: str = '7d', recipients: Optional[Iterable[str]] = None) -> None:
    from app import create_app, mail

    app = create_app()
    with app.app_context():
        window = resolve_reporting_window(period=period)
        digest_body = build_kpi_digest(window['start'], window['end'], window['label'])

        resolved_recipients = list(recipients) if recipients else _determine_digest_recipients()
        if not resolved_recipients:
            current_app.logger.warning('No recipients configured for KPI digest email.')
            return

        subject = f"Ministry KPI Digest — {window['label']}"
        msg = Message(subject=subject, recipients=resolved_recipients, body=digest_body)
        mail.send(msg)
        current_app.logger.info(
            "KPI digest dispatched to %s", ', '.join(resolved_recipients))


def schedule_kpi_digest(period: str = '7d', recipients: Optional[Iterable[str]] = None) -> Optional[str]:
    from app import create_app

    job_id: Optional[str] = None
    try:
        queue = getattr(current_app, 'task_queue', None)
        if queue is not None:
            job = queue.enqueue('tasks.send_kpi_digest', period, list(recipients) if recipients else None)
            current_app.logger.info('Scheduled KPI digest job %s', job.id)
            job_id = job.id
    except RuntimeError:
        app = create_app()
        with app.app_context():
            queue = getattr(app, 'task_queue', None)
            if queue is not None:
                job = queue.enqueue('tasks.send_kpi_digest', period, list(recipients) if recipients else None)
                app.logger.info('Scheduled KPI digest job %s', job.id)
                job_id = job.id
    return job_id


def trigger_automation(trigger: str, context: Dict[str, Any] | None = None) -> int:
    """Schedule automations for a trigger and return number of matched workflows."""

    context = context or {}
    automation_ids = _collect_active_automation_ids(trigger)

    if not automation_ids:
        return 0

    queue = _resolve_queue()
    if queue:
        queue.enqueue(run_automations_for_ids, automation_ids, context, trigger)
    else:
        run_automations_for_ids(automation_ids, context, trigger)

    return len(automation_ids)


def run_automations_for_ids(
    automation_ids: Iterable[int],
    context: Dict[str, Any] | None = None,
    trigger: str | None = None,
) -> None:
    """Execute the automations identified by ``automation_ids``."""

    from app import create_app

    context = context or {}
    automation_ids = list(automation_ids)
    if not automation_ids:
        return

    app = create_app()

    with app.app_context():
        active_automations = (
            Automation.query.filter(
                Automation.id.in_(list(automation_ids)),
                Automation.is_active.is_(True),
            )
            .order_by(Automation.id)
            .all()
        )

        queue = getattr(app, "task_queue", None)

        for automation in active_automations:
            _schedule_automation_steps(automation, context, trigger, queue)


def execute_automation_step(
    step_id: int, context: Dict[str, Any] | None = None, trigger: str | None = None
) -> None:
    """Execute a single automation step."""

    from app import create_app, mail

    context = context or {}
    app = create_app()

    with app.app_context():
        step = AutomationStep.query.get(step_id)
        if not step or not step.automation or not step.automation.is_active:
            return

        expanded_context = _expand_context(context, trigger, step.automation)

        try:
            if step.action_type == "email":
                _run_email_action(step, expanded_context, mail)
            elif step.action_type == "sms":
                _run_sms_action(step, expanded_context)
            elif step.action_type == "assignment":
                _run_assignment_action(step, expanded_context)
            else:
                current_app.logger.warning(
                    "Unknown automation action type '%s' for step %s",
                    step.action_type,
                    step.id,
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            current_app.logger.exception(
                "Error executing automation step %s: %s", step.id, exc
            )


def _collect_active_automation_ids(trigger: str) -> List[int]:
    """Return active automation IDs for a trigger, handling missing context."""

    def _query_ids() -> List[int]:
        return [
            automation.id
            for automation in Automation.query.filter_by(
                trigger=trigger, is_active=True
            ).all()
        ]

    try:
        return _query_ids()
    except RuntimeError:
        from app import create_app

        app = create_app()
        with app.app_context():
            return _query_ids()


def _resolve_queue():
    """Return the configured task queue if available."""

    try:
        queue = getattr(current_app, "task_queue", None)
        if queue:
            return queue
    except RuntimeError:
        return None

    return None


def _schedule_automation_steps(
    automation: Automation,
    context: Dict[str, Any],
    trigger: str | None,
    queue,
) -> None:
    """Schedule each step in an automation for execution."""

    ordered_steps = sorted(
        automation.steps,
        key=lambda step: ((step.order or 0), step.id),
    )

    for step in ordered_steps:
        step_context = dict(context)
        if queue:
            delay = max(step.delay_minutes or 0, 0)
            if delay:
                queue.enqueue_in(
                    timedelta(minutes=delay),
                    execute_automation_step,
                    step.id,
                    step_context,
                    trigger,
                )
            else:
                queue.enqueue(
                    execute_automation_step,
                    step.id,
                    step_context,
                    trigger,
                )
        else:
            execute_automation_step(step.id, step_context, trigger)


def _expand_context(
    context: Dict[str, Any],
    trigger: str | None,
    automation: Automation,
) -> Dict[str, Any]:
    """Hydrate context with database objects referenced by identifiers."""

    expanded = dict(context)
    expanded.setdefault("trigger", trigger)
    expanded.setdefault("automation_name", automation.name)
    expanded.setdefault("automation_id", automation.id)

    if "prayer_request_id" in expanded and "prayer_request" not in expanded:
        prayer = PrayerRequest.query.get(expanded["prayer_request_id"])
        if prayer:
            expanded["prayer_request"] = prayer
            expanded.setdefault("submitter_email", prayer.email)

    if "event_id" in expanded and "event" not in expanded:
        event = Event.query.get(expanded["event_id"])
        if event:
            expanded["event"] = event

    if "sermon_id" in expanded and "sermon" not in expanded:
        sermon = Sermon.query.get(expanded["sermon_id"])
        if sermon:
            expanded["sermon"] = sermon

    if "user_id" in expanded and "user" not in expanded:
        user = User.query.get(expanded["user_id"])
        if user:
            expanded["user"] = user

    return expanded


def _run_email_action(
    step: AutomationStep,
    context: Dict[str, Any],
    mail,
) -> None:
    config = step.config or {}

    recipients = _resolve_recipients(step, config, context)
    if not recipients:
        current_app.logger.info(
            "Skipping automation email step %s because no recipients were resolved",
            step.id,
        )
        return

    render_context = dict(context)
    render_context.update({"step": step, "automation": step.automation})

    subject_template = config.get("subject") or step.title or step.automation.name
    body_template = config.get("body") or ""

    subject = render_template_string(subject_template, **render_context).strip()
    body = render_template_string(body_template, **render_context)

    message = Message(subject=subject, recipients=recipients, body=body)
    mail.send(message)

    current_app.logger.info(
        "Automation email step %s sent to %s recipient(s)",
        step.id,
        len(recipients),
    )


def _run_sms_action(step: AutomationStep, context: Dict[str, Any]) -> None:
    config = step.config or {}
    recipients = _resolve_recipients(step, config, context)
    message_template = config.get("message") or config.get("body") or ""

    if not recipients:
        current_app.logger.info(
            "No SMS recipients resolved for automation step %s", step.id
        )
        return

    render_context = dict(context)
    render_context.update({"step": step, "automation": step.automation})
    message = render_template_string(message_template, **render_context)

    current_app.logger.info(
        "SMS automation step %s would notify %s via channel '%s': %s",
        step.id,
        ", ".join(recipients),
        step.channel or "sms",
        message,
    )


def _run_assignment_action(step: AutomationStep, context: Dict[str, Any]) -> None:
    config = step.config or {}
    department = step.department or config.get("department")
    assignee = config.get("assignee")
    notes = config.get("notes") or config.get("body")

    render_context = dict(context)
    render_context.update({"step": step, "automation": step.automation})

    formatted_notes = (
        render_template_string(notes, **render_context) if notes else ""
    )

    current_app.logger.info(
        "Automation step %s assigned to department '%s' (assignee: %s). %s",
        step.id,
        department or "unspecified",
        assignee or "n/a",
        formatted_notes,
    )


def _resolve_recipients(
    step: AutomationStep,
    config: Dict[str, Any],
    context: Dict[str, Any],
) -> List[str]:
    """Resolve recipients from configuration and context."""

    def _split(value: str | None) -> List[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    recipient_mode = (config.get("recipient_mode") or "custom").lower()
    recipients: List[str] = []

    if recipient_mode == "admins":
        recipients = [
            user.email
            for user in User.query.filter_by(is_admin=True).all()
            if user.email
        ]
    elif recipient_mode == "context":
        key = config.get("context_key") or "submitter_email"
        value = context.get(key)
        if isinstance(value, str):
            recipients = [value]
        elif isinstance(value, (list, tuple, set)):
            recipients = [item for item in value if isinstance(item, str)]
    elif recipient_mode == "department":
        recipients = _split(config.get("department_emails"))
    else:  # custom
        recipients = _split(config.get("recipients"))

    if not recipients:
        recipients = _split(config.get("fallback_recipients"))

    if not recipients and step.department:
        recipients = _split(config.get("department_emails"))

    return recipients
