from flask import Blueprint, render_template, flash, current_app
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
