from collections import defaultdict
from datetime import datetime, timezone
from itertools import zip_longest

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

 codex/expand-event-model-for-recurrence-and-tags
from app import db
from models import Event

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from models import Event, VolunteerAssignment, VolunteerRole
     main

events_bp = Blueprint('events', __name__)


 codex/expand-event-model-for-recurrence-and-tags
def _filter_events_by_tag(events, tag):
    if not tag:
        return events

    tag_lower = tag.lower()
    filtered = []
    for event in events:
        tags = event.ministry_tags or []
        if any(existing.lower() == tag_lower for existing in tags):
            filtered.append(event)
    return filtered


def _escape_ics_text(value):
    if not value:
        return ''
    return (
        value.replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _format_ics_datetime(value):
    if not value:
        return ''
    if value.tzinfo is None:
        return value.strftime('%Y%m%dT%H%M%SZ')
    return value.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _serialize_event(event):
    return {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'start': event.start_date.isoformat() if event.start_date else None,
        'end': event.end_date.isoformat() if event.end_date else None,
        'location': event.location,
        'recurrence_rule': event.recurrence_rule,
        'recurrence_end': (
            event.recurrence_end_date.isoformat()
            if event.recurrence_end_date
            else None
        ),
        'service_segments': event.service_segments or [],
        'ministry_tags': event.ministry_tags or [],
    }


     main
@events_bp.route('/events')
def events():
    tag_filter = request.args.get('tag')

    try:
 codex/expand-event-model-for-recurrence-and-tags
        events_query = Event.query.order_by(Event.start_date)
        events_all = events_query.all()
        available_tags = sorted(
            {
                tag
                for event in events_all
                for tag in (event.ministry_tags or [])
            }
        )
        events_list = _filter_events_by_tag(events_all, tag_filter)

        return render_template(
            'events.html',
            events=events_list,
            tag_filter=tag_filter,
            available_tags=available_tags,
        )
    except SQLAlchemyError as exc:
        current_app.logger.error(
            'Database error while fetching events: %s', exc
        )
        events_list = (
            Event.query.options(
                joinedload(Event.department),
                joinedload(Event.volunteer_role)
                .joinedload(VolunteerRole.coordinator),
                joinedload(Event.volunteer_role)
                .joinedload(VolunteerRole.assignments)
                .joinedload(VolunteerAssignment.volunteer),
            )
            .order_by(Event.start_date)
            .all()
        )
        return render_template('events.html', events=events_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error while fetching events: {str(e)}")
     main
        flash('Unable to load events at this time. Please try again later.', 'danger')
        return render_template(
            'events.html',
            events=[],
            tag_filter=tag_filter,
            available_tags=[],
        )
    except Exception as exc:  # noqa: BLE001 - broad exception to surface to the UI
        current_app.logger.error('Unexpected error in events route: %s', exc)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template(
            'events.html',
            events=[],
            tag_filter=tag_filter,
            available_tags=[],
        )


@events_bp.route('/events/<int:event_id>')
def event_detail(event_id):
    try:
 codex/expand-event-model-for-recurrence-and-tags
        event = db.session.get(Event, event_id)
        event = (
            Event.query.options(
                joinedload(Event.department),
                joinedload(Event.volunteer_role)
                .joinedload(VolunteerRole.coordinator),
                joinedload(Event.volunteer_role)
                .joinedload(VolunteerRole.assignments)
                .joinedload(VolunteerAssignment.volunteer),
            )
            .get(event_id)
        )
     main
        if not event:
            flash('Event not found.', 'warning')
            return redirect(url_for('events.events'))

        upcoming_events = (
            Event.query.options(joinedload(Event.department))
            .filter(Event.start_date >= datetime.utcnow(), Event.id != event_id)
            .order_by(Event.start_date)
            .limit(3)
            .all()
        )

        return render_template(
            'event_detail.html',
            event=event,
            upcoming_events=upcoming_events,
        )
    except SQLAlchemyError as exc:
        current_app.logger.error(
            'Database error while fetching event %s: %s', event_id, exc
        )
        flash('Unable to load the event at this time. Please try again later.', 'danger')
        return redirect(url_for('events.events'))
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error(
            'Unexpected error in event_detail route: %s', exc
        )
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('events.events'))


@events_bp.route('/events/plan/<int:event_id>', methods=['GET', 'POST'])
def plan_event(event_id):
    event = Event.query.get_or_404(event_id)
    printable = request.args.get('format') == 'print'

    if request.method == 'POST':
        event.recurrence_rule = request.form.get('recurrence_rule', '').strip() or None

        recurrence_end_input = request.form.get('recurrence_end')
        if recurrence_end_input:
            try:
                event.recurrence_end_date = datetime.strptime(
                    recurrence_end_input, '%Y-%m-%d'
                )
            except ValueError:
                flash('Invalid recurrence end date. Use YYYY-MM-DD format.', 'warning')
        else:
            event.recurrence_end_date = None

        raw_tags = request.form.get('ministry_tags', '')
        event.ministry_tags = [
            tag.strip()
            for tag in raw_tags.split(',')
            if tag.strip()
        ]

        titles = request.form.getlist('segment_title')
        leaders = request.form.getlist('segment_leader')
        durations = request.form.getlist('segment_duration')
        notes = request.form.getlist('segment_notes')
        segments = []
        for title, leader, duration, note in zip_longest(
            titles, leaders, durations, notes, fillvalue=''
        ):
            if not any([title, leader, duration, note]):
                continue
            segments.append(
                {
                    'title': (title or '').strip(),
                    'leader': (leader or '').strip(),
                    'duration': (duration or '').strip(),
                    'notes': (note or '').strip(),
                }
            )
        event.service_segments = segments

        try:
            db.session.commit()
            flash('Planning details saved for this event.', 'success')
            return redirect(url_for('events.plan_event', event_id=event.id))
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.error(
                'Database error while saving plan for event %s: %s', event_id, exc
            )
            flash(
                'An error occurred while updating the event plan. Please try again.',
                'danger',
            )

    segments_for_form = event.service_segments or []
    if not segments_for_form:
        segments_for_form = [
            {'title': '', 'leader': '', 'duration': '', 'notes': ''}
        ]

    planned_segments = [
        segment
        for segment in event.service_segments or []
        if any(segment.values())
    ]

    return render_template(
        'events_plan.html',
        event=event,
        segments=segments_for_form,
        planned_segments=planned_segments,
        printable=printable,
    )


@events_bp.route('/calendar')
def departmental_calendar():
    try:
        events_all = Event.query.order_by(Event.start_date).all()
        grouped_events = defaultdict(list)
        for event in events_all:
            tags = event.ministry_tags or ['General Ministry']
            for tag in tags:
                grouped_events[tag].append(event)

        for tag, items in grouped_events.items():
            items.sort(key=lambda item: item.start_date)

        return render_template(
            'calendar/index.html',
            grouped_events=grouped_events,
        )
    except SQLAlchemyError as exc:
        current_app.logger.error('Error loading departmental calendar: %s', exc)
        flash('Unable to load the calendar right now. Please try again later.', 'danger')
        return render_template(
            'calendar/index.html',
            grouped_events={},
        )


@events_bp.route('/api/events.json')
def events_json_feed():
    tag_filter = request.args.get('tag')
    events_all = Event.query.order_by(Event.start_date).all()
    events_filtered = _filter_events_by_tag(events_all, tag_filter)
    return jsonify([_serialize_event(event) for event in events_filtered])


@events_bp.route('/api/events.ics')
def events_ical_feed():
    tag_filter = request.args.get('tag')
    events_all = Event.query.order_by(Event.start_date).all()
    events_filtered = _filter_events_by_tag(events_all, tag_filter)

    calendar_name = f"{tag_filter or 'All Ministries'} Schedule"
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//Covenant Connect//Departmental Calendar//EN',
        f'X-WR-CALNAME:{_escape_ics_text(calendar_name)}',
    ]

    timestamp = _format_ics_datetime(datetime.utcnow())

    for event in events_filtered:
        lines.extend(
            [
                'BEGIN:VEVENT',
                f'UID:event-{event.id}@covenantconnect',
                f'DTSTAMP:{timestamp}',
                f'SUMMARY:{_escape_ics_text(event.title)}',
            ]
        )

        start_formatted = _format_ics_datetime(event.start_date)
        if start_formatted:
            lines.append(f'DTSTART:{start_formatted}')

        end_formatted = _format_ics_datetime(event.end_date)
        if end_formatted:
            lines.append(f'DTEND:{end_formatted}')

        description = _escape_ics_text(event.description or '')
        if description:
            lines.append(f'DESCRIPTION:{description}')

        if event.location:
            lines.append(f'LOCATION:{_escape_ics_text(event.location)}')

        if event.recurrence_rule:
            lines.append(f'RRULE:{event.recurrence_rule}')

        if event.ministry_tags:
            category_line = ','.join(
                _escape_ics_text(tag) for tag in event.ministry_tags
            )
            lines.append(f'CATEGORIES:{category_line}')

        lines.append('END:VEVENT')

    lines.append('END:VCALENDAR')

    ics_data = '\r\n'.join(lines) + '\r\n'
    filename = f"{(tag_filter or 'all').replace(' ', '_').lower()}_events.ics"

    return Response(
        ics_data,
        mimetype='text/calendar',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
