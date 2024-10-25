from flask import Blueprint, render_template, current_app, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import PrayerRequest, Event, Sermon, Donation, User, Gallery
from app import db
from sqlalchemy import func
from datetime import datetime, time
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
import csv
import io

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

@admin_bp.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent removing admin status from self
        if user.id == current_user.id:
            flash('You cannot remove your own admin status.', 'danger')
            return redirect(url_for('admin.users'))

        user.is_admin = not user.is_admin
        db.session.commit()
        
        flash(f"Admin status {'granted to' if user.is_admin else 'removed from'} {user.username}.", 'success')
    except Exception as e:
        current_app.logger.error(f"Error toggling admin status: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating admin status.', 'danger')
    
    return redirect(url_for('admin.users'))

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

@admin_bp.route('/admin/users/import', methods=['GET', 'POST'])
@login_required
@admin_required
def user_import():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if not file or file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        if not file.filename.endswith('.csv'):
            flash('Only CSV files are allowed.', 'danger')
            return redirect(request.url)

        try:
            # Read CSV file
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            success_count = 0
            error_count = 0
            errors = []

            for row in csv_input:
                try:
                    if not all(k in row for k in ['username', 'email', 'password']):
                        error_count += 1
                        errors.append(f"Missing required fields in row")
                        continue

                    # Check if user already exists
                    if User.query.filter((User.username == row['username']) | 
                                      (User.email == row['email'])).first():
                        error_count += 1
                        errors.append(f"User with username {row['username']} or email {row['email']} already exists")
                        continue

                    # Create new user
                    user = User()
                    user.username = row['username']
                    user.email = row['email']
                    user.is_admin = row.get('is_admin', '').lower() == 'true'
                    user.set_password(row['password'])
                    db.session.add(user)
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"Error processing row: {str(e)}")

            db.session.commit()
            
            flash(f'Successfully imported {success_count} users. {error_count} errors occurred.', 
                  'success' if error_count == 0 else 'warning')
            if errors:
                for error in errors[:5]:  # Show only first 5 errors
                    flash(error, 'danger')
                if len(errors) > 5:
                    flash(f'... and {len(errors) - 5} more errors', 'danger')

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error importing users: {str(e)}")
            flash('An error occurred while importing users.', 'danger')

        return redirect(url_for('admin.users'))

    return render_template('admin/user_import.html')

# Prayer Request Management Routes
@admin_bp.route('/admin/prayers')
@login_required
@admin_required
def prayers():
    try:
        prayers_list = PrayerRequest.query.order_by(PrayerRequest.created_at.desc()).all()
        return render_template('admin/prayers.html', prayers=prayers_list)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in prayers route: {str(e)}")
        flash('An error occurred while fetching prayer requests.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error in prayers route: {str(e)}")
        flash('An unexpected error occurred.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/prayers/<int:prayer_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_prayer_visibility(prayer_id):
    try:
        prayer = PrayerRequest.query.get_or_404(prayer_id)
        prayer.is_public = not prayer.is_public
        db.session.commit()
        flash(f'Prayer request visibility updated to {prayer.is_public}.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error toggling prayer visibility: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating the prayer request.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error toggling prayer visibility: {str(e)}")
        db.session.rollback()
        flash('An unexpected error occurred.', 'danger')
    
    return redirect(url_for('admin.prayers'))

@admin_bp.route('/admin/prayers/<int:prayer_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_prayer(prayer_id):
    try:
        prayer = PrayerRequest.query.get_or_404(prayer_id)
        db.session.delete(prayer)
        db.session.commit()
        flash('Prayer request deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting prayer: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting the prayer request.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting prayer: {str(e)}")
        db.session.rollback()
        flash('An unexpected error occurred.', 'danger')
    
    return redirect(url_for('admin.prayers'))

# Sermons Management Routes
@admin_bp.route('/admin/sermons')
@login_required
@admin_required
def sermons():
    try:
        sermons_list = Sermon.query.order_by(Sermon.date.desc()).all()
        return render_template('admin/sermons.html', sermons=sermons_list)
    except Exception as e:
        current_app.logger.error(f"Error fetching sermons: {str(e)}")
        flash('An error occurred while fetching sermons.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/sermons/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_sermon():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            preacher = request.form.get('preacher')
            date = request.form.get('date')
            media_url = request.form.get('media_url')
            media_type = request.form.get('media_type')

            if not all([title, date, media_url, media_type]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/sermon_form.html')

            sermon = Sermon()
            sermon.title = title
            sermon.description = description
            sermon.preacher = preacher
            sermon.date = datetime.strptime(date, '%Y-%m-%d')
            sermon.media_url = media_url
            sermon.media_type = media_type

            db.session.add(sermon)
            db.session.commit()
            flash('Sermon created successfully.', 'success')
            return redirect(url_for('admin.sermons'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating sermon: {str(e)}")
            flash('An error occurred while creating the sermon.', 'danger')
            return render_template('admin/sermon_form.html')

    return render_template('admin/sermon_form.html')

@admin_bp.route('/admin/sermons/<int:sermon_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_sermon(sermon_id):
    sermon = Sermon.query.get_or_404(sermon_id)
    
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            preacher = request.form.get('preacher')
            date = request.form.get('date')
            media_url = request.form.get('media_url')
            media_type = request.form.get('media_type')

            if not all([title, date, media_url, media_type]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/sermon_form.html', sermon=sermon)

            sermon.title = title
            sermon.description = description
            sermon.preacher = preacher
            if date:
                sermon.date = datetime.strptime(date, '%Y-%m-%d')
            sermon.media_url = media_url
            sermon.media_type = media_type

            db.session.commit()
            flash('Sermon updated successfully.', 'success')
            return redirect(url_for('admin.sermons'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating sermon: {str(e)}")
            flash('An error occurred while updating the sermon.', 'danger')
            return render_template('admin/sermon_form.html', sermon=sermon)

    return render_template('admin/sermon_form.html', sermon=sermon)

@admin_bp.route('/admin/sermons/<int:sermon_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_sermon(sermon_id):
    try:
        sermon = Sermon.query.get_or_404(sermon_id)
        db.session.delete(sermon)
        db.session.commit()
        flash('Sermon deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting sermon: {str(e)}")
        flash('An error occurred while deleting the sermon.', 'danger')
    
    return redirect(url_for('admin.sermons'))

# Gallery Management Routes
@admin_bp.route('/admin/gallery')
@login_required
@admin_required
def gallery():
    try:
        images = Gallery.query.order_by(Gallery.created_at.desc()).all()
        return render_template('admin/gallery.html', images=images)
    except Exception as e:
        current_app.logger.error(f"Error fetching gallery images: {str(e)}")
        flash('An error occurred while fetching gallery images.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/gallery/upload', methods=['POST'])
@login_required
@admin_required
def upload_image():
    try:
        if 'image' not in request.files:
            flash('No image file uploaded.', 'danger')
            return redirect(url_for('admin.gallery'))

        image = request.files['image']
        if not image.filename:
            flash('No image selected.', 'danger')
            return redirect(url_for('admin.gallery'))

        # TODO: Implement actual image upload logic here
        # For now, we'll just store the URL
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        image_url = f"/static/uploads/{image.filename}"  # Placeholder URL

        gallery_item = Gallery()
        gallery_item.title = title
        gallery_item.description = description
        gallery_item.image_url = image_url

        db.session.add(gallery_item)
        db.session.commit()

        flash('Image uploaded successfully.', 'success')
        return redirect(url_for('admin.gallery'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading image: {str(e)}")
        flash('An error occurred while uploading the image.', 'danger')
        return redirect(url_for('admin.gallery'))

@admin_bp.route('/admin/gallery/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_image(image_id):
    try:
        image = Gallery.query.get_or_404(image_id)
        db.session.delete(image)
        db.session.commit()
        flash('Image deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting image: {str(e)}")
        flash('An error occurred while deleting the image.', 'danger')
    
    return redirect(url_for('admin.gallery'))

# Donation Management Route
@admin_bp.route('/admin/donations')
@login_required
@admin_required
def donations():
    try:
        donations_list = Donation.query.order_by(Donation.created_at.desc()).all()
        return render_template('admin/donations.html', donations=donations_list)
    except Exception as e:
        current_app.logger.error(f"Error fetching donations: {str(e)}")
        flash('An error occurred while fetching donations.', 'danger')
        return redirect(url_for('admin.dashboard'))

# Event Management Routes
@admin_bp.route('/admin/events')
@login_required
@admin_required
def events():
    try:
        events_list = Event.query.order_by(Event.start_date.desc()).all()
        now = datetime.utcnow()
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
            location = request.form.get('location')
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            end_date = request.form.get('end_date')
            end_time = request.form.get('end_time')
            
            if not all([title, start_date, start_time, end_date, end_time, location]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/event_form.html')
            
            # Combine date and time
            start_datetime = datetime.combine(
                datetime.strptime(start_date, '%Y-%m-%d').date(),
                datetime.strptime(start_time, '%H:%M').time()
            )
            end_datetime = datetime.combine(
                datetime.strptime(end_date, '%Y-%m-%d').date(),
                datetime.strptime(end_time, '%H:%M').time()
            )
            
            if end_datetime <= start_datetime:
                flash('End date/time must be after start date/time.', 'danger')
                return render_template('admin/event_form.html')
            
            event = Event()
            event.title = title
            event.description = description
            event.location = location
            event.start_date = start_datetime
            event.end_date = end_datetime
            
            db.session.add(event)
            db.session.commit()
            
            flash('Event created successfully.', 'success')
            return redirect(url_for('admin.events'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating event: {str(e)}")
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
            location = request.form.get('location')
            start_date = request.form.get('start_date')
            start_time = request.form.get('start_time')
            end_date = request.form.get('end_date')
            end_time = request.form.get('end_time')
            
            if not all([title, start_date, start_time, end_date, end_time, location]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/event_form.html', event=event)
            
            # Combine date and time
            start_datetime = datetime.combine(
                datetime.strptime(start_date, '%Y-%m-%d').date(),
                datetime.strptime(start_time, '%H:%M').time()
            )
            end_datetime = datetime.combine(
                datetime.strptime(end_date, '%Y-%m-%d').date(),
                datetime.strptime(end_time, '%H:%M').time()
            )
            
            if end_datetime <= start_datetime:
                flash('End date/time must be after start date/time.', 'danger')
                return render_template('admin/event_form.html', event=event)
            
            event.title = title
            event.description = description
            event.location = location
            event.start_date = start_datetime
            event.end_date = end_datetime
            
            db.session.commit()
            flash('Event updated successfully.', 'success')
            return redirect(url_for('admin.events'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating event: {str(e)}")
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
        db.session.rollback()
        current_app.logger.error(f"Error deleting event: {str(e)}")
        flash('An error occurred while deleting the event.', 'danger')
    
    return redirect(url_for('admin.events'))
