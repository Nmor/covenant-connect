from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required
from app import db, mail
from models import PrayerRequest, User
from flask_mail import Message

prayers_bp = Blueprint('prayers', __name__)

@prayers_bp.route('/prayers', methods=['GET'])
def prayers():
    public_prayers = PrayerRequest.query.filter_by(is_public=True).order_by(PrayerRequest.created_at.desc()).all()
    return render_template('prayers.html', prayers=public_prayers)

def send_prayer_notification(prayer_request):
    try:
        # Get all admin users to notify
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
Public: {"Yes" if prayer_request.is_public else "No"}
Submitted: {prayer_request.created_at.strftime('%B %d, %Y %I:%M %p')}
        """
        
        msg = Message(
            subject=subject,
            recipients=[admin.email for admin in admin_users],
            body=body
        )
        
        mail.send(msg)
        current_app.logger.info(f"Prayer request notification sent to {len(admin_users)} admin(s)")
    except Exception as e:
        current_app.logger.error(f"Failed to send prayer request notification: {str(e)}")

@prayers_bp.route('/prayers/submit', methods=['POST'])
def submit_prayer():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        prayer_request = request.form.get('request')
        is_public = bool(request.form.get('is_public'))

        if not all([name, email, prayer_request]):
            flash('Please fill all required fields', 'error')
            return redirect(url_for('prayers.prayers'))

        new_prayer = PrayerRequest(
            name=name,
            email=email,
            request=prayer_request,
            is_public=is_public
        )
        
        db.session.add(new_prayer)
        db.session.commit()
        
        # Send email notification to admins
        send_prayer_notification(new_prayer)
        
        flash('Prayer request submitted successfully', 'success')
        return redirect(url_for('prayers.prayers'))
    except Exception as e:
        current_app.logger.error(f"Error submitting prayer request: {str(e)}")
        db.session.rollback()
        flash('An error occurred while submitting your prayer request. Please try again.', 'error')
        return redirect(url_for('prayers.prayers'))
