"""Event routes providing planning tools and public feeds."""
from __future__ import annotations

from datetime import datetime
from typing import List

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import Event


events_bp = Blueprint('events', __name__)


def _parse_service_segments() -> List[dict[str, str]]:
    """Convert repeating segment fields from the planning form into a list."""

    titles = request.form.getlist('segment_title')
    leaders = request.form.getlist('segment_leader')
    durations = request.form.getlist('segment_duration')
    notes_list = request.form.getlist('segment_notes')

    segments: List[dict[str, str]] = []
    for title, leader, duration, notes in zip(titles, leaders, durations, notes_list):
        if not any([title.strip(), leader.strip(), duration.strip(), notes.strip()]):
            continue
        segments.append(
            {
                'title': title.strip(),
                'leader': leader.strip(),
                'duration': duration.strip(),
                'notes': notes.strip(),
            }
        )
    return segments


def _normalize_tags(raw_tags: str | None) -> List[str]:
    if not raw_tags:
        return []
    return [tag.strip() for tag in raw_tags.split(',') if tag.strip()]


def _serialize_event(event: Event) -> dict[str, object]:
    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'start': event.start_date.isoformat() if event.start_date else None,
        'end': event.end_date.isoformat() if event.end_date else None,
        'location': event.location,
        'campus': event.campus,
        'recurrence_rule': event.recurrence_rule,
        'recurrence_end': (
            event.recurrence_end_date.isoformat() if event.recurrence_end_date else None
        ),
        'service_segments': event.service_segments or [],
        'ministry_tags': event.ministry_tags or [],
    }


@events_bp.route('/events')
def events() -> str:
    tag_filter = (request.args.get('tag') or '').strip()

    try:
        events_query = Event.query.order_by(Event.start_date.asc())
        events_all = events_query.all()
    except SQLAlchemyError as exc:  # pragma: no cover - logged for operators
        current_app.logger.error('Database error while fetching events: %s', exc)
        flash('Unable to load events at the moment.', 'danger')
        events_all = []

    available_tags = sorted(
        {
            tag
            for event in events_all
            for tag in (event.ministry_tags or [])
            if tag
        }
    )

    if tag_filter:
        tag_lower = tag_filter.lower()
        events_filtered = [
            event
            for event in events_all
            if any((tag or '').lower() == tag_lower for tag in (event.ministry_tags or []))
        ]
    else:
        events_filtered = events_all

    return render_template(
        'events.html',
        events=events_filtered,
        tag_filter=tag_filter,
        available_tags=available_tags,
    )


@events_bp.route('/events/plan/<int:event_id>', methods=['GET', 'POST'])
def plan_event(event_id: int):
    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        recurrence_rule = (request.form.get('recurrence_rule') or '').strip() or None
        recurrence_end_raw = (request.form.get('recurrence_end') or '').strip()
        ministry_tags_raw = request.form.get('ministry_tags')

        recurrence_end = None
        if recurrence_end_raw:
            try:
                recurrence_end = datetime.strptime(recurrence_end_raw, '%Y-%m-%d')
            except ValueError:
                flash('Invalid recurrence end date. Use YYYY-MM-DD format.', 'warning')
                return redirect(url_for('events.plan_event', event_id=event.id))

        event.recurrence_rule = recurrence_rule
        event.recurrence_end_date = recurrence_end
        event.ministry_tags = _normalize_tags(ministry_tags_raw)
        event.service_segments = _parse_service_segments()

        try:
            db.session.commit()
            flash('Event plan updated successfully.', 'success')
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.error('Error saving event plan: %s', exc)
            flash('Unable to save event plan. Please try again.', 'danger')

        return redirect(url_for('events.plan_event', event_id=event.id))

    return render_template('admin/events/plan.html', event=event)


@events_bp.route('/api/events.json')
def events_json():
    tag_filter = (request.args.get('tag') or '').strip()

    events_query = Event.query.order_by(Event.start_date.asc())
    events_all = events_query.all()

    if tag_filter:
        tag_lower = tag_filter.lower()
        events_all = [
            event
            for event in events_all
            if any((tag or '').lower() == tag_lower for tag in (event.ministry_tags or []))
        ]

    return jsonify([_serialize_event(event) for event in events_all])


def _format_ics_datetime(value: datetime | None) -> str:
    if not value:
        return ''
    return value.strftime('%Y%m%dT%H%M%S')


@events_bp.route('/api/events.ics')
def events_ics() -> Response:
    events = Event.query.order_by(Event.start_date.asc()).all()

    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Covenant Connect//EN']

    for event in events:
        lines.extend(
            [
                'BEGIN:VEVENT',
                f'SUMMARY:{event.title}',
                f'DESCRIPTION:{(event.description or "").replace("\\n", " ")}',
                f'DTSTART:{_format_ics_datetime(event.start_date)}',
                f'DTEND:{_format_ics_datetime(event.end_date)}',
                f'LOCATION:{event.location or ""}',
            ]
        )

        if event.recurrence_rule:
            lines.append(f'RRULE:{event.recurrence_rule}')
        if event.ministry_tags:
            lines.append(f'CATEGORIES:{",".join(event.ministry_tags)}')

        lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')

    body = '\r\n'.join(lines)
    response = make_response(body)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=events.ics'
    return response
