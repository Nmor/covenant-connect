from typing import Iterable, List, Optional

from flask_mail import Message
from models import PrayerRequest, User
from routes.admin_reports import build_kpi_digest, resolve_reporting_window

def send_prayer_notification(prayer_request_id: int) -> None:
    from app import create_app, mail, db
    from flask import current_app

    """Background task to send prayer notification emails to admins."""
    app = create_app()
    with app.app_context():
        prayer_request = PrayerRequest.query.get(prayer_request_id)
        if not prayer_request:
            current_app.logger.error("Prayer request not found")
            return

        admin_users = User.query.filter_by(is_admin=True).all()
        if not admin_users:
            current_app.logger.warning("No admin users found to notify about prayer request")
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
        msg = Message(subject=subject,
                      recipients=[admin.email for admin in admin_users],
                      body=body)
        mail.send(msg)
        current_app.logger.info(
            f"Prayer request notification sent to {len(admin_users)} admin(s)")


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
    from flask import current_app

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
    from flask import current_app
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
