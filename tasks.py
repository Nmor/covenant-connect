from flask_mail import Message
from models import PrayerRequest, User

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
