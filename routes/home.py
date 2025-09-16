from datetime import datetime

from flask import Blueprint, current_app, render_template
from sqlalchemy.exc import SQLAlchemyError

from models import Event, Sermon

home_bp = Blueprint('home', __name__)


@home_bp.route('/')
def home():
    """Render the homepage with featured sermons and upcoming events."""
    latest_sermons = []
    upcoming_events = []

    try:
        latest_sermons = (
            Sermon.query.order_by(Sermon.date.desc()).limit(3).all()
        )
    except SQLAlchemyError as exc:
        current_app.logger.error(
            f"Database error while fetching latest sermons: {exc}"
        )

    try:
        upcoming_events = (
            Event.query
            .filter(Event.start_date >= datetime.utcnow())
            .order_by(Event.start_date)
            .limit(3)
            .all()
        )
    except SQLAlchemyError as exc:
        current_app.logger.error(
            f"Database error while fetching upcoming events: {exc}"
        )

    return render_template(
        'home.html',
        latest_sermons=latest_sermons,
        upcoming_events=upcoming_events
    )
