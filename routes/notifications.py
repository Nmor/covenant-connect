from flask import Blueprint, jsonify, current_app
from flask_sse import sse
from flask_login import login_required, current_user

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications/subscribe')
@login_required
def subscribe():
    try:
        return jsonify({"status": "success", "message": "Subscribed to notifications"})
    except Exception as e:
        current_app.logger.error(f"Error in notifications subscribe: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_notification(user_id, message, type="info"):
    """
    Send a notification to a specific user
    """
    try:
        sse.publish(
            {"message": message, "type": type},
            type="notification",
            channel=f"user.{user_id}"
        )
    except Exception as e:
        current_app.logger.error(f"Error sending notification: {str(e)}")
