from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import Event
from tasks import trigger_automation


events_bp = Blueprint('events', __name__)


@events_bp.route('/events')
def events():
    try:
        events_list = Event.query.order_by(Event.start_date).all()
        return render_template('events.html', events=events_list)
    except SQLAlchemyError as exc:
        current_app.logger.error(
            "Database error while fetching events: %s", exc,
        )
        flash('Unable to load events at this time. Please try again later.', 'danger')
        return render_template('events.html', events=[])
    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.error("Unexpected error in events route: %s", exc)
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return render_template('events.html', events=[])


@events_bp.route('/events/<int:event_id>')
def event_detail(event_id: int):
    try:
        event = db.session.get(Event, event_id)
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

        trigger_automation('event_viewed', {'event_id': event.id})

        return render_template(
            'event_detail.html',
            event=event,
            upcoming_events=upcoming_events,
        )
    except SQLAlchemyError as exc:
        current_app.logger.error(
            "Database error while fetching event %s: %s",
            event_id,
            exc,
        )
        flash('Unable to load the event at this time. Please try again later.', 'danger')
        return redirect(url_for('events.events'))
    except Exception as exc:  # pragma: no cover - defensive logging
        current_app.logger.error(
            "Unexpected error in event_detail route: %s",
            exc,
        )
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('events.events'))
