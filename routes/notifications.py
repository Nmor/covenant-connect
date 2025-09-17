from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from app import db

notifications_bp = Blueprint('notifications', __name__)

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
            flash('Notification preferences updated successfully.', 'success')
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
        flash('An error occurred while managing notification preferences.', 'danger')
        return redirect(url_for('auth.profile'))

def add_notification(user_id, message, type="info"):
    """
    Add a notification to user's session
    """
    try:
        if 'notifications' not in session:
            session['notifications'] = []
        session['notifications'].append({
            'message': message,
            'type': type,
            'timestamp': datetime.now().isoformat()
        })
        session.modified = True
    except Exception as e:
        current_app.logger.error(f"Error adding notification: {str(e)}")

@notifications_bp.route('/notifications/get')
@login_required
def get_notifications():
    """Get current notifications from session"""
    notifications = session.get('notifications', [])
    session['notifications'] = []  # Clear after retrieving
    session.modified = True
    return jsonify(notifications)
