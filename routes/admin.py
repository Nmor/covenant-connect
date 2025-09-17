from flask import Blueprint, render_template, current_app, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import PrayerRequest, Event, Sermon, Donation, User, Gallery, Settings
from app import db
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from functools import wraps
import csv
import io
import os
from werkzeug.utils import secure_filename

from routes.admin_reports import collect_dashboard_metrics, resolve_reporting_window

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
@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    try:
        window = resolve_reporting_window(
            period=request.args.get('period'),
            start=request.args.get('start'),
            end=request.args.get('end'),
        )

        metrics = collect_dashboard_metrics(window['start'], window['end'])

        filters = {
            'label': window['label'],
            'period': window['period'],
            'start': window['start'],
            'end': window['end'],
            'start_iso': window['start'].isoformat(),
            'end_iso': window['end'].isoformat(),
        }

        if window['period'] == 'custom':
            export_args = {'start': filters['start_iso'], 'end': filters['end_iso']}
        else:
            export_args = {'period': window['period']}

        return render_template(
            'admin/dashboard/index.html',
            metrics=metrics,
            filters=filters,
            export_args=export_args,
        )

    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in dashboard route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading the dashboard.', 'danger')
        return redirect(url_for('home.home'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in dashboard route: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'danger')
        return redirect(url_for('home.home'))

# User Management Routes
@admin_bp.route('/admin/users')
@login_required
@admin_required
def users():
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in users route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading users.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in users route: {str(e)}")
        flash('An error occurred while loading users.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            is_admin = bool(request.form.get('is_admin'))
            
            user = User()
            user.username = username
            user.email = email
            user.is_admin = is_admin
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('User created successfully.', 'success')
            return redirect(url_for('admin.users'))
            
        return render_template('admin/user_form.html')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error creating user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while creating user.', 'danger')
        return redirect(url_for('admin.users'))
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        flash('An error occurred while creating user.', 'danger')
        return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        if request.method == 'POST':
            user.username = request.form['username']
            user.email = request.form['email']
            user.is_admin = bool(request.form.get('is_admin'))
            if request.form.get('password'):
                user.set_password(request.form['password'])
            db.session.commit()
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        return render_template('admin/user_form.html', user=user)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error editing user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while editing user.', 'danger')
        return redirect(url_for('admin.users'))
    except Exception as e:
        current_app.logger.error(f"Error editing user: {str(e)}")
        flash('An error occurred while editing user.', 'danger')
        return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    try:
        if current_user.id == user_id:
            flash('You cannot delete your own account.', 'danger')
            return redirect(url_for('admin.users'))
            
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting user.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        flash('An error occurred while deleting user.', 'danger')
    return redirect(url_for('admin.users'))

@admin_bp.route('/admin/users/import', methods=['GET', 'POST'])
@login_required
@admin_required
def user_import():
    try:
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file uploaded.', 'danger')
                return redirect(url_for('admin.users'))
                
            file = request.files['file']
            if not file.filename:
                flash('No selected file.', 'danger')
                return redirect(url_for('admin.users'))
                
            if file and file.filename.endswith('.csv'):
                stream = io.StringIO(file.stream.read().decode("UTF8"))
                csv_input = csv.reader(stream)
                next(csv_input)  # Skip header row
                
                for row in csv_input:
                    username, email, is_admin = row
                    user = User()
                    user.username = username
                    user.email = email
                    user.is_admin = is_admin.lower() == 'true'
                    user.set_password('changeme123')  # Default password
                    db.session.add(user)
                
                db.session.commit()
                flash('Users imported successfully.', 'success')
            else:
                flash('Please upload a CSV file.', 'danger')
                
        return redirect(url_for('admin.users'))
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error importing users: {str(e)}")
        flash('An error occurred while importing users.', 'danger')
        return redirect(url_for('admin.users'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error importing users: {str(e)}")
        flash('An error occurred while importing users.', 'danger')
        return redirect(url_for('admin.users'))

# Event Management Routes
@admin_bp.route('/admin/events')
@login_required
@admin_required
def events():
    try:
        events = Event.query.order_by(Event.start_date.desc()).all()
        return render_template('admin/events.html', events=events)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in events route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading events.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error in events route: {str(e)}")
        flash('An error occurred while loading events.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/events/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_event():
    try:
        if request.method == 'POST':
            event = Event()
            event.title = request.form['title']
            event.description = request.form['description']
            event.start_date = datetime.strptime(f"{request.form['start_date']} {request.form['start_time']}", '%Y-%m-%d %H:%M')
            event.end_date = datetime.strptime(f"{request.form['end_date']} {request.form['end_time']}", '%Y-%m-%d %H:%M')
            event.location = request.form['location']
            db.session.add(event)
            db.session.commit()
            flash('Event created successfully.', 'success')
            return redirect(url_for('admin.events'))
        return render_template('admin/event_form.html')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error creating event: {str(e)}")
        db.session.rollback()
        flash('An error occurred while creating event.', 'danger')
        return redirect(url_for('admin.events'))
    except Exception as e:
        current_app.logger.error(f"Error creating event: {str(e)}")
        flash('An error occurred while creating event.', 'danger')
        return redirect(url_for('admin.events'))

@admin_bp.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        if request.method == 'POST':
            event.title = request.form['title']
            event.description = request.form['description']
            event.start_date = datetime.strptime(f"{request.form['start_date']} {request.form['start_time']}", '%Y-%m-%d %H:%M')
            event.end_date = datetime.strptime(f"{request.form['end_date']} {request.form['end_time']}", '%Y-%m-%d %H:%M')
            event.location = request.form['location']
            db.session.commit()
            flash('Event updated successfully.', 'success')
            return redirect(url_for('admin.events'))
        return render_template('admin/event_form.html', event=event)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error editing event: {str(e)}")
        db.session.rollback()
        flash('An error occurred while editing event.', 'danger')
        return redirect(url_for('admin.events'))
    except Exception as e:
        current_app.logger.error(f"Error editing event: {str(e)}")
        flash('An error occurred while editing event.', 'danger')
        return redirect(url_for('admin.events'))

@admin_bp.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting event: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting event.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting event: {str(e)}")
        flash('An error occurred while deleting event.', 'danger')
    return redirect(url_for('admin.events'))

# Prayer Request Management Routes
@admin_bp.route('/admin/prayers')
@login_required
@admin_required
def prayers():
    try:
        prayers = PrayerRequest.query.order_by(PrayerRequest.created_at.desc()).all()
        return render_template('admin/prayers.html', prayers=prayers)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in prayers route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading prayers.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error in prayers route: {str(e)}")
        flash('An error occurred while loading prayers.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/prayers/<int:prayer_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_prayer_visibility(prayer_id):
    try:
        prayer = PrayerRequest.query.get_or_404(prayer_id)
        prayer.is_public = not prayer.is_public
        db.session.commit()
        flash('Prayer request visibility updated successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error toggling prayer visibility: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating prayer request.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error toggling prayer visibility: {str(e)}")
        flash('An error occurred while updating prayer request.', 'danger')
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
        flash('An error occurred while deleting prayer request.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting prayer: {str(e)}")
        flash('An error occurred while deleting prayer request.', 'danger')
    return redirect(url_for('admin.prayers'))

# Gallery Management Routes
@admin_bp.route('/admin/gallery')
@login_required
@admin_required
def gallery():
    try:
        images = Gallery.query.order_by(Gallery.created_at.desc()).all()
        return render_template('admin/gallery.html', images=images)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in gallery route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading gallery.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error in gallery route: {str(e)}")
        flash('An error occurred while loading gallery.', 'danger')
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
            flash('No selected file.', 'danger')
            return redirect(url_for('admin.gallery'))
            
        if image:
            filename = secure_filename(str(image.filename))
            filepath = os.path.join('static/uploads', filename)
            os.makedirs('static/uploads', exist_ok=True)
            image.save(filepath)
            
            gallery_image = Gallery()
            gallery_image.title = request.form.get('title', filename)
            gallery_image.description = request.form.get('description', '')
            gallery_image.image_url = f"/static/uploads/{filename}"
            db.session.add(gallery_image)
            db.session.commit()
            
            flash('Image uploaded successfully.', 'success')
        return redirect(url_for('admin.gallery'))
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error uploading image: {str(e)}")
        db.session.rollback()
        flash('An error occurred while uploading image.', 'danger')
        return redirect(url_for('admin.gallery'))
    except Exception as e:
        current_app.logger.error(f"Error uploading image: {str(e)}")
        flash('An error occurred while uploading image.', 'danger')
        return redirect(url_for('admin.gallery'))

@admin_bp.route('/admin/gallery/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_image(image_id):
    try:
        image = Gallery.query.get_or_404(image_id)
        # Remove the file from filesystem
        if image.image_url:
            file_path = os.path.join('static', image.image_url.lstrip('/'))
            if os.path.exists(file_path):
                os.remove(file_path)
        
        db.session.delete(image)
        db.session.commit()
        flash('Image deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting image: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting image.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting image: {str(e)}")
        flash('An error occurred while deleting image.', 'danger')
    return redirect(url_for('admin.gallery'))

# Sermon Management Routes
@admin_bp.route('/admin/sermons')
@login_required
@admin_required
def sermons():
    try:
        sermons = Sermon.query.order_by(Sermon.date.desc()).all()
        return render_template('admin/sermons.html', sermons=sermons)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in sermons route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading sermons.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error in sermons route: {str(e)}")
        flash('An error occurred while loading sermons.', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/sermons/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_sermon():
    try:
        if request.method == 'POST':
            sermon = Sermon()
            sermon.title = request.form['title']
            sermon.description = request.form['description']
            sermon.preacher = request.form['preacher']
            sermon.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            sermon.media_url = request.form['media_url']
            sermon.media_type = request.form['media_type']
            db.session.add(sermon)
            db.session.commit()
            flash('Sermon added successfully.', 'success')
            return redirect(url_for('admin.sermons'))
        return render_template('admin/sermon_form.html')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error creating sermon: {str(e)}")
        db.session.rollback()
        flash('An error occurred while creating sermon.', 'danger')
        return redirect(url_for('admin.sermons'))
    except Exception as e:
        current_app.logger.error(f"Error creating sermon: {str(e)}")
        flash('An error occurred while creating sermon.', 'danger')
        return redirect(url_for('admin.sermons'))

@admin_bp.route('/admin/sermons/<int:sermon_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_sermon(sermon_id):
    try:
        sermon = Sermon.query.get_or_404(sermon_id)
        if request.method == 'POST':
            sermon.title = request.form['title']
            sermon.description = request.form['description']
            sermon.preacher = request.form['preacher']
            sermon.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            sermon.media_url = request.form['media_url']
            sermon.media_type = request.form['media_type']
            db.session.commit()
            flash('Sermon updated successfully.', 'success')
            return redirect(url_for('admin.sermons'))
        return render_template('admin/sermon_form.html', sermon=sermon)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error editing sermon: {str(e)}")
        db.session.rollback()
        flash('An error occurred while editing sermon.', 'danger')
        return redirect(url_for('admin.sermons'))
    except Exception as e:
        current_app.logger.error(f"Error editing sermon: {str(e)}")
        flash('An error occurred while editing sermon.', 'danger')
        return redirect(url_for('admin.sermons'))

@admin_bp.route('/admin/sermons/<int:sermon_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_sermon(sermon_id):
    try:
        sermon = Sermon.query.get_or_404(sermon_id)
        db.session.delete(sermon)
        db.session.commit()
        flash('Sermon deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting sermon: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting sermon.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting sermon: {str(e)}")
        flash('An error occurred while deleting sermon.', 'danger')
    return redirect(url_for('admin.sermons'))

# Settings Management Routes
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
            settings.business_name = request.form['business_name']
            
            # Handle logo upload
            if 'logo' in request.files:
                logo_file = request.files['logo']
                if logo_file.filename:
                    filename = secure_filename(str(logo_file.filename))
                    filepath = os.path.join('static/uploads', filename)
                    os.makedirs('static/uploads', exist_ok=True)
                    logo_file.save(filepath)
                    settings.logo_url = f"/static/uploads/{filename}"
            
            # Update addresses
            addresses = request.form.getlist('addresses[]')
            settings.addresses = [addr for addr in addresses if addr]
            
            # Update social media links
            settings.social_media_links = {
                'facebook': request.form.get('social_media[facebook]'),
                'twitter': request.form.get('social_media[twitter]'),
                'instagram': request.form.get('social_media[instagram]'),
                'youtube': request.form.get('social_media[youtube]')
            }
            
            # Update contact info
            settings.contact_info = {
                'phone': request.form.get('contact_info[phone]'),
                'email': request.form.get('contact_info[email]'),
                'hours': request.form.get('contact_info[hours]')
            }
            
            db.session.commit()
            flash('Settings updated successfully.', 'success')
            return redirect(url_for('admin.settings'))
            
        return render_template('admin/settings.html', settings=settings)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error managing settings: {str(e)}")
        db.session.rollback()
        flash('An error occurred while managing settings.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error managing settings: {str(e)}")
        flash('An error occurred while managing settings.', 'danger')
        return redirect(url_for('admin.dashboard'))

# Donation Management Routes
@admin_bp.route('/admin/donations')
@login_required
@admin_required
def donations():
    try:
        donations = Donation.query.order_by(Donation.created_at.desc()).all()
        return render_template('admin/donations.html', donations=donations)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in donations route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading donations.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error in donations route: {str(e)}")
        flash('An error occurred while loading donations.', 'danger')
        return redirect(url_for('admin.dashboard'))
