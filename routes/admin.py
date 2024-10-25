from flask import Blueprint, render_template
from flask_login import login_required
from models import PrayerRequest, Event, Sermon, Donation
from sqlalchemy import func
from datetime import datetime
from decimal import Decimal

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
def dashboard():
    # Get current timestamp for comparing events
    now = datetime.utcnow()

    # Prayer Request Statistics
    prayer_stats = {
        'total': PrayerRequest.query.count(),
        'public': PrayerRequest.query.filter_by(is_public=True).count(),
        'private': PrayerRequest.query.filter_by(is_public=False).count()
    }

    # Event Statistics
    event_stats = {
        'total': Event.query.count(),
        'upcoming': Event.query.filter(Event.start_date >= now).count(),
        'past': Event.query.filter(Event.end_date < now).count()
    }

    # Sermon Statistics
    sermon_stats = {
        'total': Sermon.query.count(),
        'video': Sermon.query.filter_by(media_type='video').count(),
        'audio': Sermon.query.filter_by(media_type='audio').count()
    }

    # Donation Statistics
    successful_donations = Donation.query.filter_by(status='success')
    
    # Calculate total amount and count
    donation_totals = successful_donations.with_entities(
        func.sum(Donation.amount).label('total_amount'),
        func.count().label('total_count')
    ).first()

    total_amount = float(donation_totals.total_amount or Decimal('0.0'))
    total_count = donation_totals.total_count or 0
    average_amount = round(total_amount / total_count if total_count > 0 else 0, 2)

    # Get amounts by currency
    currency_stats = successful_donations.with_entities(
        Donation.currency,
        func.sum(Donation.amount).label('amount')
    ).group_by(Donation.currency).all()

    currency_labels = [stat.currency for stat in currency_stats]
    currency_amounts = [float(stat.amount) for stat in currency_stats]

    donation_stats = {
        'total_amount': total_amount,
        'total_count': total_count,
        'average': average_amount,
        'currency_labels': currency_labels,
        'currency_amounts': currency_amounts
    }

    # Combine all statistics
    stats = {
        'prayers': prayer_stats,
        'events': event_stats,
        'sermons': sermon_stats,
        'donations': donation_stats
    }

    return render_template('admin/dashboard.html', stats=stats)
