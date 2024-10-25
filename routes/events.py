from flask import Blueprint, render_template
from models import Event

events_bp = Blueprint('events', __name__)

@events_bp.route('/events')
def events():
    events_list = Event.query.order_by(Event.start_date).all()
    return render_template('events.html', events=events_list)
