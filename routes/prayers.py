from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app import db
from models import PrayerRequest
from tasks import send_prayer_notification

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
    name = (request.form.get('name') or '').strip()
    email = (request.form.get('email') or '').strip()
    message = (request.form.get('request') or '').strip()
    is_public = bool(request.form.get('is_public'))

    if not name or not email or not message:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('prayers.prayers'))

    prayer = PrayerRequest(name=name, email=email, request=message, is_public=is_public)
    db.session.add(prayer)
    db.session.commit()

    queue = getattr(current_app, 'task_queue', None)
    if queue is not None:
        queue.enqueue(send_prayer_notification, prayer.id)
    else:
        current_app.logger.info('Prayer notifications run immediately for %s', prayer.id)
        send_prayer_notification(prayer.id)

    flash('Prayer request submitted successfully.', 'success')
    return redirect(url_for('prayers.prayers'))
