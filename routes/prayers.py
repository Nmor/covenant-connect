from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app import db
from models import PrayerRequest
from tasks import send_prayer_notification


prayers_bp = Blueprint('prayers', __name__)


@prayers_bp.route('/prayers', methods=['GET'])
def prayers():
    prayers_list = (
        PrayerRequest.query
        .filter_by(is_public=True)
        .order_by(PrayerRequest.created_at.desc())
        .all()
    )
    return render_template('prayers.html', prayers=prayers_list)


@prayers_bp.route('/prayers/submit', methods=['POST'])
def submit_prayer():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    prayer_text = request.form.get('request', '').strip()
    is_public = bool(request.form.get('is_public'))

    if not all([name, email, prayer_text]):
        flash('Please fill all required fields', 'error')
        return redirect(url_for('prayers.prayers'))

    new_prayer = PrayerRequest(
        name=name,
        email=email,
        request=prayer_text,
        is_public=is_public,
    )

    try:
        db.session.add(new_prayer)
        db.session.commit()

        task_queue = getattr(current_app, 'task_queue', None)
        if task_queue is not None:
            task_queue.enqueue(send_prayer_notification, new_prayer.id)

        flash('Prayer request submitted successfully', 'success')
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.error('Error submitting prayer request: %s', exc)
        flash(
            'An error occurred while submitting your prayer request. Please try again.',
            'error',
        )

    return redirect(url_for('prayers.prayers'))
