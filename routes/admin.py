from flask import Blueprint, render_template, current_app, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import PrayerRequest, Event, Sermon, Donation, User, Gallery, Settings
from app import db
from sqlalchemy import func
from datetime import datetime, time
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
import csv
import io
import os
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin')
@login_required
@admin_required
def dashboard():
    try:
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
        try:
            successful_donations = Donation.query.filter_by(status='success')
            
            donation_totals = successful_donations.with_entities(
                func.sum(Donation.amount).label('total_amount'),
                func.count().label('total_count')
            ).first()

            if donation_totals and donation_totals.total_amount:
                total_amount = float(donation_totals.total_amount)
                total_count = donation_totals.total_count
                average_amount = round(total_amount / total_count, 2)
            else:
                total_amount = 0
                total_count = 0
                average_amount = 0

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
        except SQLAlchemyError as e:
            current_app.logger.error(f"Error calculating donation statistics: {str(e)}")
            donation_stats = {
                'total_amount': 0,
                'total_count': 0,
                'average': 0,
                'currency_labels': [],
                'currency_amounts': []
            }

        stats = {
            'prayers': prayer_stats,
            'events': event_stats,
            'sermons': sermon_stats,
            'donations': donation_stats
        }

        return render_template('admin/dashboard.html', stats=stats)
    except Exception as e:
        current_app.logger.error(f"Error in admin dashboard: {str(e)}")
        return render_template('admin/dashboard.html', error="An error occurred loading the dashboard")

# Business Settings Routes
@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    try:
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()

        if request.method == 'POST':
            business_name = request.form.get('business_name')
            if not business_name:
                flash('Business name is required.', 'danger')
                return render_template('admin/settings.html', settings=settings)

            settings.business_name = business_name

            # Handle logo upload
            if 'logo' in request.files:
                logo = request.files['logo']
                if logo.filename:
                    # Save the logo to static/uploads directory
                    filename = secure_filename(logo.filename)
                    upload_path = os.path.join('static', 'uploads', filename)
                    logo.save(upload_path)
                    settings.logo_url = f"/static/uploads/{filename}"

            db.session.commit()
            flash('Settings updated successfully.', 'success')
            return redirect(url_for('admin.settings'))

        return render_template('admin/settings.html', settings=settings)
    except Exception as e:
        current_app.logger.error(f"Error in settings: {str(e)}")
        flash('An error occurred while managing settings.', 'danger')
        return redirect(url_for('admin.dashboard'))

# [Previous admin routes remain unchanged...]
