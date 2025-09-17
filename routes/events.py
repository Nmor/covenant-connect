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
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import AttendanceRecord, Event, FacilityReservation


events_bp = Blueprint('events', __name__)


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


@events_bp.route('/events')
def events():
    try:
        events_list = Event.query.order_by(Event.start_date).all()
        return render_template('events.html', events=events_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error while fetching events: {str(e)}")
        flash('Unable to load events at this time. Please try again later.', 'danger')
        return render_template('events.html', events=[])
    except Exception as e:
        current_app.logger.error(f"Unexpected error in events route: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template('events.html', events=[])


@events_bp.route('/events/<int:event_id>')
def event_detail(event_id):
    try:
        event = db.session.get(Event, event_id)
        if not event:
            flash('Event not found.', 'warning')
            return redirect(url_for('events.events'))

        upcoming_events = (
            Event.query
            .filter(Event.start_date >= datetime.utcnow(), Event.id != event.id)
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
            facility_reservations=facility_reservations,
            resource_allocations=resource_allocations,
            resource_totals=resource_totals,
            total_capacity=total_capacity,
            attendance_records=attendance_records,
            expected_attendance=expected_attendance,
            total_checked_in=total_checked_in,
            last_check_in=last_check_in,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(
            f"Database error while fetching event {event_id}: {str(e)}"
        )
        flash('Unable to load the event at this time. Please try again later.', 'danger')
        return redirect(url_for('events.events'))
    except Exception as e:
        current_app.logger.error(
            f"Unexpected error in event_detail route: {str(e)}"
        )
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('events.events'))


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
