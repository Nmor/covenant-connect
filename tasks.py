"""Utility functions for asynchronous tasks and workflow automations."""

from __future__ import annotations

from datetime import timedelta
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List

from flask import current_app, render_template_string

from app import db
from models import (
    Automation,
    AutomationStep,
    Event,
    MinistryDepartment,
    PrayerRequest,
    Sermon,
    User,
)
from routes.admin_reports import ReportingService
from integrations import EmailIntegrationManager


def send_prayer_notification(prayer_request_id: int) -> None:
    from app import create_app

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
        EmailIntegrationManager.send_email(
            subject=subject,
            body=body,
            recipients=[admin.email for admin in admin_users],
        )
        current_app.logger.info(
            "Prayer request notification sent to %s admin(s)",
            len(admin_users),
        )


def send_department_kpi_digest(range_days: int = 30) -> int:
    from app import create_app

    app = create_app()
    with app.app_context():
        start = datetime.utcnow() - timedelta(days=range_days)
        end = datetime.utcnow()
        service = ReportingService(db.session)
        metrics = _collect_kpi_metrics(service, start, end)

        sent = 0
        departments = MinistryDepartment.query.filter(MinistryDepartment.lead.isnot(None)).all()
        for department in departments:
            lead = department.lead
            if not lead or not lead.email:
                continue

            body = _render_department_digest(department.name, metrics, start, end)
            subject = f"{department.name} KPI Digest ({start:%b %d} - {end:%b %d})"
            EmailIntegrationManager.send_email(
                subject=subject,
                body=body,
                recipients=[lead.email],
            )
            sent += 1

        current_app.logger.info('Sent %s department KPI digests.', sent)
        return sent


def send_executive_kpi_digest(range_days: int = 30) -> int:
    from app import create_app

    app = create_app()
    with app.app_context():
        start = datetime.utcnow() - timedelta(days=range_days)
        end = datetime.utcnow()
        service = ReportingService(db.session)
        metrics = _collect_kpi_metrics(service, start, end)

        admins = [user.email for user in User.query.filter_by(is_admin=True).all() if user.email]
        if not admins:
            current_app.logger.info('No executive recipients available for KPI digest.')
            return 0

        body = _render_executive_digest(metrics, start, end)
        subject = f"Executive KPI Summary ({start:%b %d} - {end:%b %d})"
        EmailIntegrationManager.send_email(
            subject=subject,
            body=body,
            recipients=admins,
        )
        current_app.logger.info('Sent executive KPI digest to %s recipients.', len(admins))
        return len(admins)


def schedule_kpi_digest(audience: str = 'executive', range_days: int = 30) -> None:
    audience = (audience or 'executive').lower()
    queue = _resolve_queue()
    if audience == 'department':
        func = send_department_kpi_digest
    else:
        func = send_executive_kpi_digest

    if queue:
        queue.enqueue(func, range_days)
    else:
        func(range_days)


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


def _collect_kpi_metrics(service: ReportingService, start: datetime, end: datetime) -> Dict[str, Any]:
    return {
        'attendance': service.attendance_trends(start, end),
        'volunteers': service.volunteer_fulfilment(start, end),
        'giving': service.giving_summary(start, end),
        'assimilation': service.assimilation_funnel(start, end),
    }


def _render_department_digest(name: str, metrics: Dict[str, Any], start: datetime, end: datetime) -> str:
    attendance = _department_attendance(metrics['attendance'], name)
    volunteer = _department_volunteers(metrics['volunteers'], name)
    giving_total = metrics['giving']['total']

    lines = [
        f"KPI summary for {name}",
        f"Window: {start:%b %d, %Y} - {end:%b %d, %Y}",
        "",
        f"Attendance: {attendance['checked']} checked-in of {attendance['expected']} expected (rate {attendance['rate']}%)",
        f"Volunteer coverage: {volunteer['assigned']} assigned of {volunteer['needed']} needed (rate {volunteer['rate']}%)",
        f"Giving (all ministries): ${giving_total:,.2f}",
        "",
        "Next Steps:",
        "- Review volunteer assignments for gaps.",
        "- Celebrate wins with your campus teams.",
    ]
    return "\n".join(lines)


def _render_executive_digest(metrics: Dict[str, Any], start: datetime, end: datetime) -> str:
    attendance = metrics['attendance']
    volunteer = metrics['volunteers']
    giving = metrics['giving']
    assimilation = metrics['assimilation']

    lines = [
        f"Executive KPI Summary ({start:%b %d, %Y} - {end:%b %d, %Y})",
        "",
        f"Attendance rate: {attendance['attendance_rate']}% across {len(attendance['campuses'])} campuses.",
        f"Volunteer fill rate: {volunteer['overall_rate']}% across {len(volunteer['departments'])} departments.",
        f"Giving total: ${giving['total']:,.2f} across {len(giving['by_currency'])} currencies.",
        f"Members tracked: {assimilation['total_members']} in funnel reporting.",
        "",
        "Top Opportunities:",
        "- Review campuses with low attendance rate.",
        "- Address departments under 70% volunteer coverage.",
    ]
    return "\n".join(lines)


def _department_attendance(attendance: Dict[str, Any], department: str) -> Dict[str, float]:
    checked = 0
    expected = 0
    for campus in attendance.get('campuses', []):
        for bucket in campus.get('departments', []):
            if bucket['name'] == department:
                checked += bucket.get('checked', 0)
                expected += bucket.get('expected', 0)
    rate = 0.0 if not expected else round((checked / expected) * 100, 2)
    return {'checked': checked, 'expected': expected, 'rate': rate}


def _department_volunteers(volunteers: Dict[str, Any], department: str) -> Dict[str, float]:
    assigned = 0
    needed = 0
    for dept in volunteers.get('departments', []):
        if dept['department'] == department:
            assigned += dept.get('assigned', 0)
            needed += dept.get('needed', 0)
    rate = 0.0 if not needed else round((assigned / needed) * 100, 2)
    return {'assigned': assigned, 'needed': needed, 'rate': rate}

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

    EmailIntegrationManager.send_email(
        subject=subject,
        body=body,
        recipients=recipients,
        html=body if config.get("body_format") == "html" else None,
    )

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
