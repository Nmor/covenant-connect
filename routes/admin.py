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

# Event Management Routes
@admin_bp.route('/admin/events')
@login_required
@admin_required
def events():
    try:
        now = datetime.utcnow()
        events_list = Event.query.order_by(Event.start_date.desc()).all()
        return render_template('admin/events.html', events=events_list, now=now)
    except Exception as e:
        current_app.logger.error(f"Error fetching events: {str(e)}")
        flash('An error occurred while fetching events.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/events/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_event():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            end_date = request.form.get('end_date')
            end_time = request.form.get('end_time')
            location = request.form.get('location')

            if not all([title, start_date, start_time, end_date, end_time, location]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/event_form.html')

            # Combine date and time strings
            start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")

            if end_datetime <= start_datetime:
                flash('End date/time must be after start date/time.', 'danger')
                return render_template('admin/event_form.html')

            event = Event(
                title=title,
                description=description,
                start_date=start_datetime,
                end_date=end_datetime,
                location=location
            )

            db.session.add(event)
            db.session.commit()
            flash('Event created successfully.', 'success')
            return redirect(url_for('admin.events'))

        except Exception as e:
            current_app.logger.error(f"Error creating event: {str(e)}")
            db.session.rollback()
            flash('An error occurred while creating the event.', 'danger')
            return render_template('admin/event_form.html')

    return render_template('admin/event_form.html')

@admin_bp.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            end_date = request.form.get('end_date')
            end_time = request.form.get('end_time')
            location = request.form.get('location')

            if not all([title, start_date, start_time, end_date, end_time, location]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/event_form.html', event=event)

            # Combine date and time strings
            start_datetime = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")

            if end_datetime <= start_datetime:
                flash('End date/time must be after start date/time.', 'danger')
                return render_template('admin/event_form.html', event=event)

            event.title = title
            event.description = description
            event.start_date = start_datetime
            event.end_date = end_datetime
            event.location = location

            db.session.commit()
            flash('Event updated successfully.', 'success')
            return redirect(url_for('admin.events'))

        except Exception as e:
            current_app.logger.error(f"Error updating event: {str(e)}")
            db.session.rollback()
            flash('An error occurred while updating the event.', 'danger')
            return render_template('admin/event_form.html', event=event)

    return render_template('admin/event_form.html', event=event)

@admin_bp.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting event: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting the event.', 'danger')
    
    return redirect(url_for('admin.events'))

# [Previous admin routes remain unchanged...]
