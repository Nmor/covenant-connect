 codex/define-models-for-facility,-resource,-attendancerecord
import csv
import io
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    make_response,
    redirect,
    render_template,
    render_template_string,
    url_for,
)
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
     main
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from models import Event, VolunteerAssignment, VolunteerRole
     main

from app import db
from models import AttendanceRecord, Event, FacilityReservation


events_bp = Blueprint('events', __name__)


 codex/define-models-for-facility,-resource,-attendancerecord
def _safe_filename(event: Event, suffix: str) -> str:
    """Return a filesystem-friendly filename for downloads."""
    base = ''.join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in event.title.lower())
    base = '_'.join(base.split()) or f'event_{event.id}'
    return f"{base}_{suffix}"


def _collect_event_resource_data(event: Event):
    facility_reservations = (
        FacilityReservation.query
        .filter_by(event_id=event.id)
        .order_by(FacilityReservation.start_time)
        .all()
    )

    total_capacity = 0
    resource_allocations = []
    resource_totals = {}

    for reservation in facility_reservations:
        facility = reservation.facility
        if facility and facility.capacity:
            total_capacity += facility.capacity

        for allocation in reservation.resource_requests:
            resource = allocation.resource
            if not resource:
                continue

            quantity = (
                allocation.quantity_approved
                if allocation.quantity_approved is not None
                else allocation.quantity_requested
            )

            resource_totals.setdefault(resource.id, {
                'resource': resource,
                'quantity': 0,
            })
            resource_totals[resource.id]['quantity'] += quantity

            resource_allocations.append({
                'reservation': reservation,
                'resource': resource,
                'allocation': allocation,
                'quantity': quantity,
            })

    return facility_reservations, resource_allocations, resource_totals, total_capacity

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
 codex/define-models-for-facility,-resource,-attendancerecord
        event = db.session.get(Event, event_id)
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
 codex/define-models-for-facility,-resource,-attendancerecord
            Event.query
            .filter(Event.start_date >= datetime.utcnow(), Event.id != event.id)
            Event.query.options(joinedload(Event.department))
            .filter(Event.start_date >= datetime.utcnow(), Event.id != event_id)
     main
            .order_by(Event.start_date)
            .limit(3)
            .all()
        )

        (
            facility_reservations,
            resource_allocations,
            resource_totals,
            total_capacity,
        ) = _collect_event_resource_data(event)

        attendance_records = (
            AttendanceRecord.query
            .filter_by(event_id=event.id)
            .order_by(AttendanceRecord.check_in_time.desc())
            .all()
        )

        expected_attendance = sum(record.expected_attendees or 0 for record in attendance_records)
        total_checked_in = sum(record.checked_in_count or 0 for record in attendance_records)
        last_check_in = attendance_records[0].check_in_time if attendance_records else None

        return render_template(
            'event_detail.html',
            event=event,
            upcoming_events=upcoming_events,
 codex/define-models-for-facility,-resource,-attendancerecord
            facility_reservations=facility_reservations,
            resource_allocations=resource_allocations,
            resource_totals=resource_totals,
            total_capacity=total_capacity,
            attendance_records=attendance_records,
            expected_attendance=expected_attendance,
            total_checked_in=total_checked_in,
            last_check_in=last_check_in,
     main
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


 codex/define-models-for-facility,-resource,-attendancerecord
@events_bp.route('/events/<int:event_id>/attendance.csv')
def export_attendance_csv(event_id):
    try:
        event = db.session.get(Event, event_id)
        if not event:
            flash('Event not found.', 'warning')
            return redirect(url_for('events.events'))

        attendance_records = (
            AttendanceRecord.query
            .filter_by(event_id=event.id)
            .order_by(AttendanceRecord.check_in_time)
            .all()
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Check-in Time', 'Expected Attendees', 'Checked In', 'Notes'])

        for record in attendance_records:
            writer.writerow([
                record.check_in_time.strftime('%Y-%m-%d %H:%M') if record.check_in_time else '',
                record.expected_attendees or '',
                record.checked_in_count or 0,
                record.notes or '',
            ])

        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = (
            f"attachment; filename={_safe_filename(event, 'attendance.csv')}"
        )
        response.headers['Content-Type'] = 'text/csv'
        return response
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error exporting attendance for event {event_id}: {str(e)}"
        )
        flash('Unable to export attendance records right now.', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error exporting attendance for event {event_id}: {str(e)}"
        )
        flash('An unexpected error occurred while exporting attendance.', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))


@events_bp.route('/events/<int:event_id>/attendance.xlsx')
def export_attendance_excel(event_id):
    try:
        event = db.session.get(Event, event_id)
        if not event:
            flash('Event not found.', 'warning')
            return redirect(url_for('events.events'))

        attendance_records = (
            AttendanceRecord.query
            .filter_by(event_id=event.id)
            .order_by(AttendanceRecord.check_in_time)
            .all()
        )

        (
            facility_reservations,
            resource_allocations,
            resource_totals,
            total_capacity,
        ) = _collect_event_resource_data(event)

        template = """
        <html>
            <head><meta charset="utf-8" /></head>
            <body>
                <h2>{{ event.title }} Attendance Summary</h2>
                <table border="1" cellpadding="4" cellspacing="0">
                    <thead>
                        <tr>
                            <th>Check-in Time</th>
                            <th>Expected Attendees</th>
                            <th>Checked In</th>
                            <th>Notes</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if attendance_records %}
                            {% for record in attendance_records %}
                                <tr>
                                    <td>{{ record.check_in_time.strftime('%Y-%m-%d %H:%M') if record.check_in_time else '' }}</td>
                                    <td>{{ record.expected_attendees or '' }}</td>
                                    <td>{{ record.checked_in_count or 0 }}</td>
                                    <td>{{ record.notes or '' }}</td>
                                </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="4">No attendance data recorded yet.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>

                <h3 style="margin-top:20px;">Facility Assignments</h3>
                <table border="1" cellpadding="4" cellspacing="0">
                    <thead>
                        <tr>
                            <th>Facility</th>
                            <th>Ministry</th>
                            <th>Schedule</th>
                            <th>Status</th>
                            <th>Resources</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if facility_reservations %}
                            {% for reservation in facility_reservations %}
                                <tr>
                                    <td>{{ reservation.facility.name if reservation.facility else '' }}</td>
                                    <td>{{ reservation.ministry_name }}</td>
                                    <td>{{ reservation.start_time.strftime('%Y-%m-%d %H:%M') }} - {{ reservation.end_time.strftime('%Y-%m-%d %H:%M') }}</td>
                                    <td>{{ reservation.status }}</td>
                                    <td>
                                        {% if reservation.resource_requests %}
                                            {% for allocation in reservation.resource_requests %}
                                                {{ allocation.resource.name }}: {{ allocation.quantity_requested }}{% if allocation.quantity_approved is not none %} (approved {{ allocation.quantity_approved }}){% endif %}{% if not loop.last %}; {% endif %}
                                            {% endfor %}
                                        {% else %}
                                            No additional resources
                                        {% endif %}
                                    </td>
                                </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="5">No facility reservations recorded.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>

                <h3 style="margin-top:20px;">Resource Totals</h3>
                <table border="1" cellpadding="4" cellspacing="0">
                    <thead>
                        <tr>
                            <th>Resource</th>
                            <th>Total Assigned</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% if resource_totals %}
                            {% for entry in resource_totals.values() %}
                                <tr>
                                    <td>{{ entry.resource.name }}</td>
                                    <td>{{ entry.quantity }}</td>
                                </tr>
                            {% endfor %}
                        {% else %}
                            <tr>
                                <td colspan="2">No resource assignments for this event.</td>
                            </tr>
                        {% endif %}
                    </tbody>
                </table>
            </body>
        </html>
        """

        html = render_template_string(
            template,
            event=event,
            attendance_records=attendance_records,
            facility_reservations=facility_reservations,
            resource_totals=resource_totals,
        )

        response = make_response(html)
        response.headers['Content-Disposition'] = (
            f"attachment; filename={_safe_filename(event, 'attendance.xlsx')}"
        )
        response.headers['Content-Type'] = 'application/vnd.ms-excel'
        return response
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error exporting attendance Excel for event {event_id}: {str(e)}"
        )
        flash('Unable to export Excel follow-up right now.', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error exporting Excel for event {event_id}: {str(e)}"
        )
        flash('An unexpected error occurred while exporting the Excel report.', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
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
     main
