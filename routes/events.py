from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    Response,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from app import db
from models import Event

events_bp = Blueprint('events', __name__)


def _parse_segments() -> list[dict[str, str]]:
    titles = request.form.getlist('segment_title')
    leaders = request.form.getlist('segment_leader')
    durations = request.form.getlist('segment_duration')
    notes = request.form.getlist('segment_notes')

    segments: list[dict[str, str]] = []
    for idx in range(max(len(titles), len(leaders), len(durations), len(notes))):
        segment = {
            'title': titles[idx].strip() if idx < len(titles) else '',
            'leader': leaders[idx].strip() if idx < len(leaders) else '',
            'duration': durations[idx].strip() if idx < len(durations) else '',
            'notes': notes[idx].strip() if idx < len(notes) else '',
        }
        if any(segment.values()):
            segments.append(segment)
    return segments


def _filter_by_tag(events: list[Event], tag: str | None) -> list[Event]:
    if not tag:
        return events
    tag_lower = tag.lower()
    return [
        event
        for event in events
        if any(existing.lower() == tag_lower for existing in (event.ministry_tags or []))
    ]


def _serialize_event(event: Event) -> dict[str, object | None]:
    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'start': event.start_date.isoformat() if event.start_date else None,
        'end': event.end_date.isoformat() if event.end_date else None,
        'location': event.location,
        'recurrence_rule': event.recurrence_rule,
        'recurrence_end': event.recurrence_end_date.isoformat()
        if event.recurrence_end_date
        else None,
        'service_segments': event.service_segments or [],
        'ministry_tags': event.ministry_tags or [],
    }


def _format_ics_datetime(value: datetime | None) -> str:
    if not value:
        return ''
    return value.strftime('%Y%m%dT%H%M%SZ')


def _escape_ics_text(value: str | None) -> str:
    if not value:
        return ''
    return (
        value.replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _build_ics(events: list[Event]) -> str:
    lines: list[str] = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Covenant Connect//Events//EN',
    ]

    now = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    for event in events:
        lines.append('BEGIN:VEVENT')
        lines.append(f'UID:event-{event.id}@covenant-connect')
        lines.append(f'DTSTAMP:{now}')
        lines.append(f'SUMMARY:{_escape_ics_text(event.title)}')
        lines.append(f'DESCRIPTION:{_escape_ics_text(event.description)}')
        lines.append(f'DTSTART:{_format_ics_datetime(event.start_date)}')
        lines.append(f'DTEND:{_format_ics_datetime(event.end_date)}')
        lines.append(f'LOCATION:{_escape_ics_text(event.location)}')
        if event.recurrence_rule:
            lines.append(f'RRULE:{event.recurrence_rule}')
        if event.ministry_tags:
            lines.append('CATEGORIES:' + ','.join(event.ministry_tags))
        lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')
    return '\r\n'.join(lines) + '\r\n'


@events_bp.route('/events')
def events():
    tag_filter = request.args.get('tag')
    events_all = Event.query.order_by(Event.start_date).all()
    filtered = _filter_by_tag(events_all, tag_filter)
    available_tags = sorted({tag for event in events_all for tag in (event.ministry_tags or [])})
    return render_template(
        'events.html',
        events=filtered,
        available_tags=available_tags,
        tag_filter=tag_filter,
    )


@events_bp.route('/events/plan/<int:event_id>', methods=['GET', 'POST'])
def plan_event(event_id: int):
    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        event.recurrence_rule = (request.form.get('recurrence_rule') or '').strip() or None
        recurrence_end = (request.form.get('recurrence_end') or '').strip()
        if recurrence_end:
            try:
                event.recurrence_end_date = datetime.strptime(recurrence_end, '%Y-%m-%d')
            except ValueError:
                event.recurrence_end_date = None
        else:
            event.recurrence_end_date = None

        raw_tags = request.form.get('ministry_tags') or ''
        event.set_ministry_tags(raw_tags.split(','))
        event.set_service_segments(_parse_segments())

        db.session.commit()
        return redirect(url_for('events.plan_event', event_id=event.id))

    return render_template('events_plan.html', event=event)


@events_bp.route('/api/events.json')
def events_json() -> Response:
    tag_filter = request.args.get('tag')
    events_all = Event.query.order_by(Event.start_date).all()
    filtered = _filter_by_tag(events_all, tag_filter)
    return jsonify([_serialize_event(event) for event in filtered])


@events_bp.route('/api/events.ics')
def events_ics() -> Response:
    events_all = Event.query.order_by(Event.start_date).all()
    body = _build_ics(events_all)
    response = make_response(body)
    response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename="events.ics"'
    return response
