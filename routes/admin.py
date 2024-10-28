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
        # [Previous dashboard code remains unchanged...]
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

# User Management Routes
@admin_bp.route('/admin/users')
@login_required
@admin_required
def users():
    try:
        users_list = User.query.all()
        return render_template('admin/users.html', users=users_list)
    except Exception as e:
        current_app.logger.error(f"Error fetching users: {str(e)}")
        flash('An error occurred while fetching users.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            is_admin = bool(request.form.get('is_admin'))

            if not all([username, email, password, confirm_password]):
                flash('All fields are required.', 'danger')
                return render_template('admin/user_form.html')

            if password != confirm_password:
                flash('Passwords do not match.', 'danger')
                return render_template('admin/user_form.html')

            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash('Username or email already exists.', 'danger')
                return render_template('admin/user_form.html')

            user = User()
            user.username = username
            user.email = email
            user.is_admin = is_admin
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()

            flash('User created successfully.', 'success')
            return redirect(url_for('admin.users'))

        except Exception as e:
            current_app.logger.error(f"Error creating user: {str(e)}")
            db.session.rollback()
            flash('An error occurred while creating the user.', 'danger')
            return render_template('admin/user_form.html')

    return render_template('admin/user_form.html')

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            is_admin = bool(request.form.get('is_admin'))

            if not all([username, email]):
                flash('All fields are required.', 'danger')
                return render_template('admin/user_form.html', user=user)

            existing_user = User.query.filter(
                (User.username == username) | (User.email == email),
                User.id != user_id
            ).first()

            if existing_user:
                flash('Username or email already exists.', 'danger')
                return render_template('admin/user_form.html', user=user)

            user.username = username
            user.email = email
            user.is_admin = is_admin
            db.session.commit()

            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.users'))

        except Exception as e:
            current_app.logger.error(f"Error updating user: {str(e)}")
            db.session.rollback()
            flash('An error occurred while updating the user.', 'danger')
            return render_template('admin/user_form.html', user=user)

    return render_template('admin/user_form.html', user=user)

@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting self
        if user.id == current_user.id:
            flash('You cannot delete your own account.', 'danger')
            return redirect(url_for('admin.users'))

        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {user.username} has been deleted.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting the user.', 'danger')
    
    return redirect(url_for('admin.users'))

# [Previous code for other admin routes remains unchanged...]
