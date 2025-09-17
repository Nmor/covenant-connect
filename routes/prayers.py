from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app

from app import db
from models import PrayerRequest
from tasks import send_prayer_notification, trigger_automation

prayers_bp = Blueprint('prayers', __name__)


@prayers_bp.route('/prayers', methods=['GET'])
def prayers():
    public_prayers = (
        PrayerRequest.query.filter_by(is_public=True)
        .order_by(PrayerRequest.created_at.desc())
        .all()
    )
    return render_template('prayers.html', prayers=public_prayers)


@prayers_bp.route('/prayers/submit', methods=['POST'])
def submit_prayer():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        prayer_request_text = request.form.get('request')
        is_public = bool(request.form.get('is_public'))

        if not all([name, email, prayer_request_text]):
            flash('Please fill all required fields', 'error')
            return redirect(url_for('prayers.prayers'))

        new_prayer = PrayerRequest(
            name=name,
            email=email,
            request=prayer_request_text,
            is_public=is_public,
        )

        db.session.add(new_prayer)
        db.session.commit()

        triggered = trigger_automation(
            'prayer_request_created',
            {'prayer_request_id': new_prayer.id},
        )

        if triggered == 0:
            queue = getattr(current_app, 'task_queue', None)
            if queue:
                queue.enqueue(send_prayer_notification, new_prayer.id)
            else:
                send_prayer_notification(new_prayer.id)

        flash('Prayer request submitted successfully', 'success')
        return redirect(url_for('prayers.prayers'))
    except Exception as exc:
        current_app.logger.error(f"Error submitting prayer request: {exc}")
        db.session.rollback()
        flash(
            'An error occurred while submitting your prayer request. Please try again.',
            'error',
        )
        return redirect(url_for('prayers.prayers'))
