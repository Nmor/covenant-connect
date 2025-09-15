from flask import Blueprint, render_template
from flask_login import login_required
from models import User, Donation, PrayerRequest, Event

internal_bp = Blueprint('internal', __name__)

@internal_bp.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'users': User.query.count(),
        'donations': Donation.query.count(),
        'prayers': PrayerRequest.query.count(),
        'events': Event.query.count()
    }
    return render_template('internal/dashboard.html', stats=stats)
