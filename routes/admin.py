from flask import Blueprint, render_template, current_app, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import (
    Automation,
    AutomationStep,
    Donation,
    Event,
    Gallery,
    PrayerRequest,
    Sermon,
    Settings,
    User,
)
from app import db
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, time
from decimal import Decimal
from functools import wraps
import csv
import io
import json
import os
from werkzeug.utils import secure_filename

from tasks import trigger_automation


AUTOMATION_TRIGGER_CHOICES = [
    ('prayer_request_created', 'Prayer request submitted'),
    ('event_created', 'Event created'),
    ('event_viewed', 'Event viewed'),
    ('sermon_published', 'Sermon published'),
    ('sermon_viewed', 'Sermon viewed'),
    ('member_status_changed', 'Member status changed'),
]

AUTOMATION_ACTION_TYPES = [
    ('email', 'Send Email'),
    ('sms', 'Send SMS'),
    ('assignment', 'Assignment / Task'),
]

DEFAULT_CHANNEL_OPTIONS = ['email', 'sms', 'app']

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def _safe_json_loads(value: str | None, default: dict | None = None) -> dict:
    """Parse a JSON string from form input, providing helpful errors."""

    if value is None or not value.strip():
        return {} if default is None else default

    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError('JSON value must be an object')
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f'Invalid JSON: {exc.msg}') from exc


def _update_automation_from_form(automation: Automation) -> None:
    """Populate an automation model instance from posted form data."""

    automation.name = request.form.get('name', '').strip()
    if not automation.name:
        raise ValueError('Automation name is required.')

    automation.trigger = request.form.get('trigger') or automation.trigger
    automation.description = request.form.get('description') or None
    automation.is_active = bool(request.form.get('is_active'))
    automation.default_channel = request.form.get('default_channel') or None
    automation.target_department = request.form.get('target_department') or None
    automation.trigger_filters = _safe_json_loads(
        request.form.get('trigger_filters'),
        automation.trigger_filters or {},
    )

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
        original_admin_state = user.is_admin
        if request.method == 'POST':
            user.username = request.form['username']
            user.email = request.form['email']
            user.is_admin = bool(request.form.get('is_admin'))
            if request.form.get('password'):
                user.set_password(request.form['password'])
            db.session.commit()
            status_changes = {}
            if original_admin_state != user.is_admin:
                status_changes['is_admin'] = {
                    'previous': original_admin_state,
                    'current': user.is_admin,
                }
            if status_changes:
                trigger_automation(
                    'member_status_changed',
                    {'user_id': user.id, 'changes': status_changes},
                )
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


# Automation Workflow Routes
@admin_bp.route('/admin/automations')
@login_required
@admin_required
def automations():
    automations_list = (
        Automation.query.order_by(Automation.created_at.desc()).all()
    )
    return render_template(
        'admin/automations/index.html',
        automations=automations_list,
    )


@admin_bp.route('/admin/automations/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_automation():
    automation = Automation(
        trigger=AUTOMATION_TRIGGER_CHOICES[0][0],
        is_active=True,
    )

    if request.method == 'POST':
        try:
            _update_automation_from_form(automation)
            db.session.add(automation)
            db.session.commit()
            flash('Automation created successfully.', 'success')
            return redirect(
                url_for('admin.automation_detail', automation_id=automation.id)
            )
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.error(
                f"Database error creating automation: {exc}"
            )
            flash('An error occurred while creating the automation.', 'danger')
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error creating automation: {exc}"
            )
            flash(
                'An unexpected error occurred while creating the automation.',
                'danger',
            )

    trigger_filters_value = (
        request.form.get('trigger_filters')
        if request.method == 'POST'
        else json.dumps(automation.trigger_filters or {}, indent=2)
    )

    return render_template(
        'admin/automations/form.html',
        automation=automation,
        trigger_choices=AUTOMATION_TRIGGER_CHOICES,
        channel_options=DEFAULT_CHANNEL_OPTIONS,
        trigger_filters=trigger_filters_value,
    )


@admin_bp.route('/admin/automations/<int:automation_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_automation(automation_id: int):
    automation = Automation.query.get_or_404(automation_id)

    if request.method == 'POST':
        try:
            _update_automation_from_form(automation)
            db.session.commit()
            flash('Automation updated successfully.', 'success')
            return redirect(
                url_for('admin.automation_detail', automation_id=automation.id)
            )
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), 'danger')
        except SQLAlchemyError as exc:
            db.session.rollback()
            current_app.logger.error(
                f"Database error updating automation {automation_id}: {exc}"
            )
            flash('An error occurred while updating the automation.', 'danger')
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(
                f"Unexpected error updating automation {automation_id}: {exc}"
            )
            flash(
                'An unexpected error occurred while updating the automation.',
                'danger',
            )

    trigger_filters_value = (
        request.form.get('trigger_filters')
        if request.method == 'POST'
        else json.dumps(automation.trigger_filters or {}, indent=2)
    )

    return render_template(
        'admin/automations/form.html',
        automation=automation,
        trigger_choices=AUTOMATION_TRIGGER_CHOICES,
        channel_options=DEFAULT_CHANNEL_OPTIONS,
        trigger_filters=trigger_filters_value,
    )


@admin_bp.route('/admin/automations/<int:automation_id>')
@login_required
@admin_required
def automation_detail(automation_id: int):
    automation = Automation.query.get_or_404(automation_id)

    step_configs = {
        step.id: json.dumps(step.config or {}, indent=2)
        for step in automation.steps
    }

    default_step_config = json.dumps(
        {
            'recipient_mode': 'admins',
            'subject': 'New notification from {{ automation.name }}',
            'body': 'Update details can use values in {{ context }}.',
        },
        indent=2,
    )

    return render_template(
        'admin/automations/detail.html',
        automation=automation,
        action_types=AUTOMATION_ACTION_TYPES,
        channel_options=DEFAULT_CHANNEL_OPTIONS,
        step_configs=step_configs,
        default_step_config=default_step_config,
    )


@admin_bp.route('/admin/automations/<int:automation_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_automation(automation_id: int):
    automation = Automation.query.get_or_404(automation_id)
    try:
        db.session.delete(automation)
        db.session.commit()
        flash('Automation deleted successfully.', 'success')
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.error(
            f"Database error deleting automation {automation_id}: {exc}"
        )
        flash('An error occurred while deleting the automation.', 'danger')
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error deleting automation {automation_id}: {exc}"
        )
        flash('An unexpected error occurred while deleting the automation.', 'danger')

    return redirect(url_for('admin.automations'))


@admin_bp.route('/admin/automations/<int:automation_id>/steps/save', methods=['POST'])
@login_required
@admin_required
def save_automation_step(automation_id: int):
    automation = Automation.query.get_or_404(automation_id)
    step_id_raw = request.form.get('step_id')

    try:
        if step_id_raw:
            step_id = int(step_id_raw)
            step = AutomationStep.query.filter_by(
                id=step_id, automation_id=automation.id
            ).first_or_404()
        else:
            step = AutomationStep(automation=automation)

        step.title = request.form.get('title') or None
        step.action_type = request.form.get('action_type') or 'email'
        if step.action_type not in {choice[0] for choice in AUTOMATION_ACTION_TYPES}:
            raise ValueError('Invalid action type selected.')

        step.channel = request.form.get('channel') or None
        step.department = request.form.get('department') or None

        order_value = request.form.get('order')
        delay_value = request.form.get('delay_minutes')

        step.order = int(order_value) if order_value else len(automation.steps) + 1
        step.delay_minutes = int(delay_value) if delay_value else 0

        config_value = request.form.get('config')
        step.config = _safe_json_loads(config_value, step.config or {})

        db.session.add(step)
        db.session.commit()
        flash('Automation step saved successfully.', 'success')
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), 'danger')
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.error(
            f"Database error saving automation step for automation {automation_id}: {exc}"
        )
        flash('An error occurred while saving the automation step.', 'danger')
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error saving automation step for automation {automation_id}: {exc}"
        )
        flash(
            'An unexpected error occurred while saving the automation step.',
            'danger',
        )

    return redirect(url_for('admin.automation_detail', automation_id=automation.id))


@admin_bp.route(
    '/admin/automations/<int:automation_id>/steps/<int:step_id>/delete',
    methods=['POST'],
)
@login_required
@admin_required
def delete_automation_step(automation_id: int, step_id: int):
    automation = Automation.query.get_or_404(automation_id)
    try:
        step = AutomationStep.query.filter_by(
            id=step_id, automation_id=automation.id
        ).first_or_404()
        db.session.delete(step)
        db.session.commit()
        flash('Automation step deleted successfully.', 'success')
    except SQLAlchemyError as exc:
        db.session.rollback()
        current_app.logger.error(
            f"Database error deleting automation step {step_id}: {exc}"
        )
        flash('An error occurred while deleting the automation step.', 'danger')
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(
            f"Unexpected error deleting automation step {step_id}: {exc}"
        )
        flash('An unexpected error occurred while deleting the automation step.', 'danger')

    return redirect(url_for('admin.automation_detail', automation_id=automation.id))


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
            trigger_automation('event_created', {'event_id': event.id})
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
            trigger_automation('sermon_published', {'sermon_id': sermon.id})
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
