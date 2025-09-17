from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from models import Event, VolunteerAssignment, VolunteerRole

events_bp = Blueprint('events', __name__)


@events_bp.route('/events')
def events():
    try:
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
        flash('Unable to load events at this time. Please try again later.', 'danger')
        return render_template('events.html', events=[])
    except Exception as e:
        current_app.logger.error(f"Unexpected error in events route: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template('events.html', events=[])


@events_bp.route('/events/<int:event_id>')
def event_detail(event_id):
    try:
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
            upcoming_events=upcoming_events
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
