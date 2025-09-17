from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app import db, task_queue
from models import CareInteraction, Member, PrayerRequest
from tasks import send_prayer_notification, trigger_automation

prayers_bp = Blueprint('prayers', __name__)


def _find_member_by_email(email: Optional[str]) -> Optional[Member]:
    if not email:
        return None
    normalized = email.strip().lower()
    if not normalized:
        return None
    return Member.query.filter(func.lower(Member.email) == normalized).first()


def _record_prayer_interaction(member: Member, prayer: PrayerRequest, is_public: bool) -> None:
    interaction_time = datetime.utcnow()
    follow_up_required = not is_public
    follow_up_date = interaction_time + timedelta(days=2) if follow_up_required else None

    interaction = CareInteraction(
        member=member,
        interaction_type='prayer_request',
        interaction_date=interaction_time,
        notes=f'Prayer request submitted: {prayer.request[:200]}',
        follow_up_required=follow_up_required,
        follow_up_date=follow_up_date,
        source='prayer_form',
        metadata_json={'prayer_request_id': prayer.id, 'is_public': is_public},
    )

    member.last_interaction_at = interaction_time
    if follow_up_required:
        if not member.next_follow_up_date or follow_up_date < member.next_follow_up_date:
            member.next_follow_up_date = follow_up_date
    if 'prayer_connection' not in (member.milestones or {}):
        member.record_milestone('prayer_connection', 'Shared a Prayer Request', completed=True)

    db.session.add(interaction)


def _enqueue_notification(prayer_id: int) -> None:
    try:
        if task_queue:
            task_queue.enqueue(send_prayer_notification, prayer_id)
        elif hasattr(current_app, 'task_queue') and current_app.task_queue:
            current_app.task_queue.enqueue(send_prayer_notification, prayer_id)
    except Exception as exc:  # pragma: no cover - background queue best effort
        current_app.logger.warning("Unable to enqueue prayer notification: %s", exc)


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
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        prayer_text = (request.form.get('request') or '').strip()
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

        db.session.add(new_prayer)
        db.session.flush()

        member = _find_member_by_email(email)
        if member:
            _record_prayer_interaction(member, new_prayer, is_public)

        db.session.commit()

        triggered = trigger_automation(
            'prayer_request_created',
            {'prayer_request_id': new_prayer.id},
        )

        if triggered == 0:
            _enqueue_notification(new_prayer.id)

        flash('Prayer request submitted successfully', 'success')
        return redirect(url_for('prayers.prayers'))
    except SQLAlchemyError as exc:
        current_app.logger.error('Database error submitting prayer request: %s', exc)
        db.session.rollback()
        flash('An error occurred while submitting your prayer request. Please try again.', 'error')
        return redirect(url_for('prayers.prayers'))
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error('Unexpected error submitting prayer request: %s', exc)
        db.session.rollback()
        flash('An error occurred while submitting your prayer request. Please try again.', 'error')
        return redirect(url_for('prayers.prayers'))
