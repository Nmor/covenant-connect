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
@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    try:
        # Add dashboard statistics
        prayer_stats = {
            'total': PrayerRequest.query.count(),
            'public': PrayerRequest.query.filter_by(is_public=True).count(),
            'private': PrayerRequest.query.filter_by(is_public=False).count()
        }
        
        event_stats = {
            'upcoming': Event.query.filter(Event.start_date >= datetime.now()).count(),
            'past': Event.query.filter(Event.end_date < datetime.now()).count(),
            'total': Event.query.count()
        }
        
        sermon_stats = {
            'total': Sermon.query.count(),
            'video': Sermon.query.filter_by(media_type='video').count(),
            'audio': Sermon.query.filter_by(media_type='audio').count()
        }
        
        donation_stats = {
            'total': Donation.query.filter_by(status='success').count(),
            'amount': db.session.query(func.sum(Donation.amount)).filter_by(status='success').scalar() or 0
        }
        
        return render_template('admin/dashboard.html',
                             prayer_stats=prayer_stats,
                             event_stats=event_stats,
                             sermon_stats=sermon_stats,
                             donation_stats=donation_stats)
                             
    except Exception as e:
        current_app.logger.error(f"Error in dashboard route: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'danger')
        return redirect(url_for('home.home'))

@admin_bp.route('/admin/users')
@login_required
@admin_required
def users():
    try:
        users = User.query.all()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        current_app.logger.error(f"Error in users route: {str(e)}")
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
            
            user = User(username=username, email=email, is_admin=is_admin)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('User created successfully.', 'success')
            return redirect(url_for('admin.users'))
            
        return render_template('admin/user_form.html')
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        flash('An error occurred while creating user.', 'danger')
        return redirect(url_for('admin.users'))

# Gallery Management Routes
@admin_bp.route('/admin/gallery')
@login_required
@admin_required
def gallery():
    try:
        images = Gallery.query.order_by(Gallery.created_at.desc()).all()
        return render_template('admin/gallery.html', images=images)
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
            flash('No image file provided.', 'danger')
            return redirect(url_for('admin.gallery'))
        
        image_file = request.files['image']
        if not image_file.filename:
            flash('No image file selected.', 'danger')
            return redirect(url_for('admin.gallery'))
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not '.' in image_file.filename or \
           image_file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            flash('Invalid file type. Allowed types: PNG, JPG, JPEG, GIF', 'danger')
            return redirect(url_for('admin.gallery'))
        
        # Secure the filename and save the file
        filename = secure_filename(image_file.filename)
        filepath = os.path.join('static/uploads', filename)
        
        # Ensure uploads directory exists
        os.makedirs('static/uploads', exist_ok=True)
        
        # Save the file
        image_file.save(filepath)
        
        # Create gallery entry
        image = Gallery()
        image.title = request.form.get('title', filename)
        image.description = request.form.get('description', '')
        image.image_url = f"/static/uploads/{filename}"
        
        db.session.add(image)
        db.session.commit()
        
        flash('Image uploaded successfully.', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error uploading image: {str(e)}")
        db.session.rollback()
        flash('An error occurred while uploading the image.', 'danger')
    
    return redirect(url_for('admin.gallery'))

@admin_bp.route('/admin/gallery/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_image(image_id):
    try:
        image = Gallery.query.get_or_404(image_id)
        
        # Delete the physical file
        if image.image_url:
            file_path = os.path.join('static', image.image_url.lstrip('/'))
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                current_app.logger.error(f"Error deleting image file: {str(e)}")
        
        # Delete database record
        db.session.delete(image)
        db.session.commit()
        
        flash('Image deleted successfully.', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error deleting image: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting the image.', 'danger')
    
    return redirect(url_for('admin.gallery'))
