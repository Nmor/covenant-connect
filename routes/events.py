from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
 codex/find-current-location-in-codebase-ntia0s
from app import db
     main
from models import Event
from sqlalchemy.exc import SQLAlchemyError

events_bp = Blueprint('events', __name__)

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
 codex/find-current-location-in-codebase-ntia0s
        event = db.session.get(Event, event_id)
        event = Event.query.get(event_id)
        main
        if not event:
            flash('Event not found.', 'warning')
            return redirect(url_for('events.events'))

        upcoming_events = (
            Event.query
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
