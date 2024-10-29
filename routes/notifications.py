from flask import Blueprint, jsonify, current_app, render_template, request, flash, redirect, url_for
from flask_sse import sse
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from models import User

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications/subscribe')
@login_required
def subscribe():
    try:
        return sse.stream()
    except Exception as e:
        current_app.logger.error(f"Error in notifications subscribe: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@notifications_bp.route('/notifications/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    try:
        if request.method == 'POST':
            current_user.notification_preferences = {
                'prayer_requests': request.form.get('prayer_requests') == 'on',
                'events': request.form.get('events') == 'on',
                'sermons': request.form.get('sermons') == 'on',
                'donations': request.form.get('donations') == 'on',
                'news': request.form.get('news') == 'on',
                'desktop': request.form.get('desktop') == 'on',
                'email': request.form.get('email') == 'on'
            }
            db.session.commit()
            flash(_('Notification preferences updated successfully.'), 'success')
            return redirect(url_for('notifications.preferences'))
            
        return render_template(
            'notifications/preferences.html',
            preferences=current_user.notification_preferences or {
                'prayer_requests': True,
                'events': True,
                'sermons': True,
                'donations': True,
                'news': True,
                'desktop': True,
                'email': True
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error managing notification preferences: {str(e)}")
        flash(_('An error occurred while managing notification preferences.'), 'danger')
        return redirect(url_for('auth.profile'))

def send_notification(user_id, message, type="info"):
    """
    Send a notification to a specific user
    """
    try:
        user = User.query.get(user_id)
        if not user or not user.notification_preferences.get(type, True):
            return
            
        sse.publish(
            {"message": message, "type": type},
            type="notification",
            channel=f"user.{user_id}"
        )
    except Exception as e:
        current_app.logger.error(f"Error sending notification: {str(e)}")
