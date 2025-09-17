from flask import Blueprint, render_template, current_app, flash, redirect, url_for, request
from flask_login import login_required, current_user
from models import (
    PrayerRequest,
    Event,
    Sermon,
    Donation,
    User,
    Gallery,
    Settings,
 codex/add-member-models-and-management-views
    Member,
    Household,
    CareInteraction,
    MinistryDepartment,
    VolunteerRole,
    VolunteerAssignment,
     main
)
from app import db
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
 codex/add-member-models-and-management-views
from datetime import datetime
from sqlalchemy.orm import joinedload
from datetime import datetime, time
     main
from decimal import Decimal
from functools import wraps
import csv
import io
import os
from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

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

        members = Member.query.all()
        connected_statuses = {'member', 'partner', 'regular', 'active'}
        connected_members = sum(
            1
            for member in members
            if (member.membership_status or '').strip().lower() in connected_statuses
        )
        followups_due = sum(1 for member in members if member.follow_up_due)
        milestone_percentages = [member.milestone_completion_rate * 100 for member in members]
        avg_milestone = round(sum(milestone_percentages) / len(milestone_percentages), 1) if milestone_percentages else 0.0

        member_stats = {
            'total': len(members),
            'connected': connected_members,
            'followups_due': followups_due,
            'milestone_completion_rate': avg_milestone,
        }

        recent_followups = (
            CareInteraction.query.options(
                joinedload(CareInteraction.member),
                joinedload(CareInteraction.created_by),
            )
            .order_by(CareInteraction.interaction_date.desc())
            .limit(5)
            .all()
        )

        return render_template('admin/dashboard.html',
                             prayer_stats=prayer_stats,
                             event_stats=event_stats,
                             sermon_stats=sermon_stats,
                             donation_stats=donation_stats,
                             member_stats=member_stats,
                             recent_followups=recent_followups)
                             
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


@admin_bp.route('/admin/members')
@login_required
@admin_required
def members():
    try:
        status_filter = (request.args.get('status') or '').strip()
        search = (request.args.get('q') or '').strip()

        query = Member.query

        if status_filter:
            query = query.filter(func.lower(Member.membership_status) == status_filter.lower())

        if search:
            like_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Member.first_name.ilike(like_pattern),
                    Member.last_name.ilike(like_pattern),
                    Member.email.ilike(like_pattern),
                )
            )

        members = query.order_by(Member.last_name.asc(), Member.first_name.asc()).all()
        statuses = [
            value[0]
            for value in (
                db.session.query(Member.membership_status)
                .distinct()
                .order_by(Member.membership_status.asc())
                .all()
            )
            if value[0]
        ]

        return render_template(
            'admin/members/index.html',
            members=members,
            statuses=statuses,
            status_filter=status_filter,
            search=search,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in members route: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading members.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in members route: {str(e)}")
        flash('An error occurred while loading members.', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/members/<int:member_id>')
@login_required
@admin_required
def member_profile(member_id):
    try:
        member = (
            Member.query.options(
                joinedload(Member.household),
                joinedload(Member.care_interactions).joinedload(CareInteraction.created_by),
            )
            .get_or_404(member_id)
        )
        interactions = sorted(
            member.care_interactions,
            key=lambda interaction: interaction.interaction_date,
            reverse=True,
        )
        milestone_data = member.milestones or {}
        default_keys = {key for key, _ in Member.DEFAULT_MILESTONES}
        extra_milestones = [
            (key, value)
            for key, value in milestone_data.items()
            if key not in default_keys
        ]
        return render_template(
            'admin/members/detail.html',
            member=member,
            interactions=interactions,
            milestone_catalog=Member.DEFAULT_MILESTONES,
            extra_milestones=extra_milestones,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error loading member {member_id}: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading the member profile.', 'danger')
        return redirect(url_for('admin.members'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error loading member {member_id}: {str(e)}")
        flash('An error occurred while loading the member profile.', 'danger')
        return redirect(url_for('admin.members'))


@admin_bp.route('/admin/members/<int:member_id>/follow-ups', methods=['POST'])
@login_required
@admin_required
def log_member_follow_up(member_id):
    try:
        member = Member.query.get_or_404(member_id)

        interaction_type = (request.form.get('interaction_type') or 'follow_up').strip() or 'follow_up'
        notes = (request.form.get('notes') or '').strip()
        interaction_date_raw = (request.form.get('interaction_date') or '').strip()
        follow_up_required = bool(request.form.get('follow_up_required'))
        follow_up_date_raw = (request.form.get('follow_up_date') or '').strip()
        assimilation_stage = (request.form.get('assimilation_stage') or '').strip()
        membership_status = (request.form.get('membership_status') or '').strip()
        milestone_key = (request.form.get('milestone_key') or '').strip()
        milestone_completed = bool(request.form.get('milestone_completed'))

        interaction_date = datetime.utcnow()
        if interaction_date_raw:
            try:
                interaction_date = datetime.strptime(interaction_date_raw, '%Y-%m-%d')
            except ValueError:
                flash('Invalid interaction date format. Using today instead.', 'warning')

        follow_up_date = None
        if follow_up_date_raw:
            try:
                follow_up_date = datetime.strptime(follow_up_date_raw, '%Y-%m-%d')
            except ValueError:
                flash('Invalid follow-up date format. Ignoring provided date.', 'warning')

        interaction = CareInteraction(
            member=member,
            interaction_type=interaction_type,
            interaction_date=interaction_date,
            notes=notes or None,
            follow_up_required=follow_up_required,
            follow_up_date=follow_up_date,
            created_by_id=current_user.id if current_user.is_authenticated else None,
            source='admin_follow_up',
            metadata={'recorded_via': 'admin_portal'},
        )

        member.last_interaction_at = interaction_date
        if follow_up_required and follow_up_date:
            member.next_follow_up_date = follow_up_date
        elif not follow_up_required:
            member.next_follow_up_date = None

        if assimilation_stage:
            member.assimilation_stage = assimilation_stage

        if membership_status:
            member.membership_status = membership_status

        if milestone_key:
            member.record_milestone(milestone_key, completed=milestone_completed)

        db.session.add(interaction)
        db.session.commit()

        flash('Follow-up recorded successfully.', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error logging follow-up for member {member_id}: {str(e)}")
        flash('An error occurred while saving the follow-up.', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error logging follow-up for member {member_id}: {str(e)}")
        flash('An unexpected error occurred while saving the follow-up.', 'danger')

    return redirect(url_for('admin.member_profile', member_id=member_id))

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
        events = (
            Event.query.options(
                joinedload(Event.department),
                joinedload(Event.volunteer_role).joinedload(VolunteerRole.department),
                joinedload(Event.volunteer_role).joinedload(VolunteerRole.coordinator),
            )
            .order_by(Event.start_date.desc())
            .all()
        )
        return render_template('admin/events.html', events=events, now=datetime.now())
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
        departments = MinistryDepartment.query.order_by(MinistryDepartment.name).all()
        roles = (
            VolunteerRole.query.options(joinedload(VolunteerRole.department))
            .order_by(VolunteerRole.name)
            .all()
        )
        if request.method == 'POST':
            event = Event()
            event.title = request.form['title']
            event.description = request.form['description']
            event.start_date = datetime.strptime(f"{request.form['start_date']} {request.form['start_time']}", '%Y-%m-%d %H:%M')
            event.end_date = datetime.strptime(f"{request.form['end_date']} {request.form['end_time']}", '%Y-%m-%d %H:%M')
            event.location = request.form['location']
            department_id = request.form.get('department_id')
            role_id = request.form.get('volunteer_role_id')
            event.department_id = int(department_id) if department_id else None
            event.volunteer_role_id = int(role_id) if role_id else None

            if event.department_id and not db.session.get(MinistryDepartment, event.department_id):
                flash('Selected department could not be found.', 'danger')
                return render_template(
                    'admin/event_form.html',
                    event=event,
                    departments=departments,
                    roles=roles,
                )

            if event.volunteer_role_id:
                role = db.session.get(VolunteerRole, event.volunteer_role_id)
                if not role:
                    flash('Selected serving role could not be found.', 'danger')
                    return render_template(
                        'admin/event_form.html',
                        event=event,
                        departments=departments,
                        roles=roles,
                    )
                if event.department_id and role.department_id != event.department_id:
                    flash('Selected role does not belong to the chosen department.', 'danger')
                    return render_template(
                        'admin/event_form.html',
                        event=event,
                        departments=departments,
                        roles=roles,
                    )
            db.session.add(event)
            db.session.commit()
            flash('Event created successfully.', 'success')
            return redirect(url_for('admin.events'))
        return render_template(
            'admin/event_form.html',
            departments=departments,
            roles=roles,
        )
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
        departments = MinistryDepartment.query.order_by(MinistryDepartment.name).all()
        roles = (
            VolunteerRole.query.options(joinedload(VolunteerRole.department))
            .order_by(VolunteerRole.name)
            .all()
        )
        if request.method == 'POST':
            event.title = request.form['title']
            event.description = request.form['description']
            event.start_date = datetime.strptime(f"{request.form['start_date']} {request.form['start_time']}", '%Y-%m-%d %H:%M')
            event.end_date = datetime.strptime(f"{request.form['end_date']} {request.form['end_time']}", '%Y-%m-%d %H:%M')
            event.location = request.form['location']
            department_id = request.form.get('department_id')
            role_id = request.form.get('volunteer_role_id')
            event.department_id = int(department_id) if department_id else None
            event.volunteer_role_id = int(role_id) if role_id else None

            if event.department_id and not db.session.get(MinistryDepartment, event.department_id):
                flash('Selected department could not be found.', 'danger')
                return render_template(
                    'admin/event_form.html',
                    event=event,
                    departments=departments,
                    roles=roles,
                )

            if event.volunteer_role_id:
                role = db.session.get(VolunteerRole, event.volunteer_role_id)
                if not role:
                    flash('Selected serving role could not be found.', 'danger')
                    return render_template(
                        'admin/event_form.html',
                        event=event,
                        departments=departments,
                        roles=roles,
                    )
                if event.department_id and role.department_id != event.department_id:
                    flash('Selected role does not belong to the chosen department.', 'danger')
                    return render_template(
                        'admin/event_form.html',
                        event=event,
                        departments=departments,
                        roles=roles,
                    )
            db.session.commit()
            flash('Event updated successfully.', 'success')
            return redirect(url_for('admin.events'))
        return render_template(
            'admin/event_form.html',
            event=event,
            departments=departments,
            roles=roles,
        )
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

# Department Management Routes
@admin_bp.route('/admin/departments')
@login_required
@admin_required
def departments():
    try:
        departments = (
            MinistryDepartment.query.options(
                joinedload(MinistryDepartment.lead),
                joinedload(MinistryDepartment.roles).joinedload(VolunteerRole.coordinator),
            )
            .order_by(MinistryDepartment.name)
            .all()
        )
        return render_template('admin/departments/index.html', departments=departments)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error loading departments: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading departments.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error loading departments: {str(e)}")
        flash('An error occurred while loading departments.', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/departments/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_department():
    try:
        users = User.query.order_by(User.username).all()
        if request.method == 'POST':
            department = MinistryDepartment()
            department.name = request.form['name']
            department.description = request.form.get('description')
            lead_id = request.form.get('lead_id')
            department.lead_id = int(lead_id) if lead_id else None
            db.session.add(department)
            db.session.commit()
            flash('Department created successfully.', 'success')
            return redirect(url_for('admin.departments'))
        return render_template('admin/departments/form.html', users=users)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error creating department: {str(e)}")
        db.session.rollback()
        flash('An error occurred while creating department.', 'danger')
        return redirect(url_for('admin.departments'))
    except Exception as e:
        current_app.logger.error(f"Error creating department: {str(e)}")
        flash('An error occurred while creating department.', 'danger')
        return redirect(url_for('admin.departments'))


@admin_bp.route('/admin/departments/<int:department_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_department(department_id):
    try:
        department = MinistryDepartment.query.get_or_404(department_id)
        users = User.query.order_by(User.username).all()
        if request.method == 'POST':
            department.name = request.form['name']
            department.description = request.form.get('description')
            lead_id = request.form.get('lead_id')
            department.lead_id = int(lead_id) if lead_id else None
            db.session.commit()
            flash('Department updated successfully.', 'success')
            return redirect(url_for('admin.departments'))
        return render_template(
            'admin/departments/form.html', department=department, users=users
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error editing department: {str(e)}")
        db.session.rollback()
        flash('An error occurred while editing department.', 'danger')
        return redirect(url_for('admin.departments'))
    except Exception as e:
        current_app.logger.error(f"Error editing department: {str(e)}")
        flash('An error occurred while editing department.', 'danger')
        return redirect(url_for('admin.departments'))


@admin_bp.route('/admin/departments/<int:department_id>')
@login_required
@admin_required
def department_detail(department_id):
    try:
        department = (
            MinistryDepartment.query.options(
                joinedload(MinistryDepartment.lead),
                joinedload(MinistryDepartment.roles)
                .joinedload(VolunteerRole.coordinator),
                joinedload(MinistryDepartment.roles)
                .joinedload(VolunteerRole.assignments)
                .joinedload(VolunteerAssignment.volunteer),
                joinedload(MinistryDepartment.events),
            )
            .get_or_404(department_id)
        )
        upcoming_events = [
            event for event in department.events if event.start_date >= datetime.now()
        ]
        upcoming_events.sort(key=lambda event: event.start_date)
        return render_template(
            'admin/departments/detail.html',
            department=department,
            upcoming_events=upcoming_events,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error loading department: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading the department.', 'danger')
        return redirect(url_for('admin.departments'))
    except Exception as e:
        current_app.logger.error(f"Error loading department: {str(e)}")
        flash('An error occurred while loading the department.', 'danger')
        return redirect(url_for('admin.departments'))


@admin_bp.route('/admin/departments/<int:department_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_department(department_id):
    try:
        department = MinistryDepartment.query.get_or_404(department_id)
        for event in list(department.events):
            event.department_id = None
            if event.volunteer_role and event.volunteer_role.department_id == department.id:
                event.volunteer_role_id = None
        for role in list(department.roles):
            for event in list(role.events):
                event.volunteer_role_id = None
        db.session.delete(department)
        db.session.commit()
        flash('Department deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting department: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting department.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting department: {str(e)}")
        flash('An error occurred while deleting department.', 'danger')
    return redirect(url_for('admin.departments'))


@admin_bp.route('/admin/departments/<int:department_id>/roles/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_role(department_id):
    try:
        department = MinistryDepartment.query.get_or_404(department_id)
        users = User.query.order_by(User.username).all()
        if request.method == 'POST':
            role = VolunteerRole()
            role.department = department
            role.name = request.form['name']
            role.description = request.form.get('description')
            coordinator_id = request.form.get('coordinator_id')
            role.coordinator_id = int(coordinator_id) if coordinator_id else None
            db.session.add(role)
            db.session.commit()
            flash('Volunteer role created successfully.', 'success')
            return redirect(url_for('admin.department_detail', department_id=department.id))
        return render_template(
            'admin/departments/role_form.html',
            department=department,
            users=users,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error creating role: {str(e)}")
        db.session.rollback()
        flash('An error occurred while creating volunteer role.', 'danger')
        return redirect(url_for('admin.department_detail', department_id=department_id))
    except Exception as e:
        current_app.logger.error(f"Error creating role: {str(e)}")
        flash('An error occurred while creating volunteer role.', 'danger')
        return redirect(url_for('admin.department_detail', department_id=department_id))


@admin_bp.route('/admin/departments/<int:department_id>/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_role(department_id, role_id):
    try:
        department = MinistryDepartment.query.get_or_404(department_id)
        role = VolunteerRole.query.get_or_404(role_id)
        if role.department_id != department.id:
            flash('Volunteer role does not belong to this department.', 'danger')
            return redirect(url_for('admin.department_detail', department_id=department.id))
        users = User.query.order_by(User.username).all()
        if request.method == 'POST':
            role.name = request.form['name']
            role.description = request.form.get('description')
            coordinator_id = request.form.get('coordinator_id')
            role.coordinator_id = int(coordinator_id) if coordinator_id else None
            db.session.commit()
            flash('Volunteer role updated successfully.', 'success')
            return redirect(url_for('admin.department_detail', department_id=department.id))
        return render_template(
            'admin/departments/role_form.html',
            department=department,
            role=role,
            users=users,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error updating role: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating volunteer role.', 'danger')
        return redirect(url_for('admin.department_detail', department_id=department_id))
    except Exception as e:
        current_app.logger.error(f"Error updating role: {str(e)}")
        flash('An error occurred while updating volunteer role.', 'danger')
        return redirect(url_for('admin.department_detail', department_id=department_id))


@admin_bp.route('/admin/departments/<int:department_id>/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_role(department_id, role_id):
    try:
        role = VolunteerRole.query.get_or_404(role_id)
        if role.department_id != department_id:
            flash('Volunteer role does not belong to the specified department.', 'danger')
            return redirect(url_for('admin.department_detail', department_id=department_id))
        for event in list(role.events):
            event.volunteer_role_id = None
        db.session.delete(role)
        db.session.commit()
        flash('Volunteer role deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting role: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting volunteer role.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting role: {str(e)}")
        flash('An error occurred while deleting volunteer role.', 'danger')
    return redirect(url_for('admin.department_detail', department_id=department_id))


# Volunteer Assignment Routes
@admin_bp.route('/admin/volunteers')
@login_required
@admin_required
def volunteers():
    try:
        assignments = (
            VolunteerAssignment.query.options(
                joinedload(VolunteerAssignment.volunteer),
                joinedload(VolunteerAssignment.role)
                .joinedload(VolunteerRole.department),
                joinedload(VolunteerAssignment.role)
                .joinedload(VolunteerRole.coordinator),
            )
            .order_by(VolunteerAssignment.created_at.desc())
            .all()
        )
        return render_template('admin/volunteers/index.html', assignments=assignments)
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error loading volunteers: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading volunteer assignments.', 'danger')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error loading volunteers: {str(e)}")
        flash('An error occurred while loading volunteer assignments.', 'danger')
        return redirect(url_for('admin.dashboard'))


@admin_bp.route('/admin/volunteers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_volunteer_assignment():
    try:
        volunteers = User.query.order_by(User.username).all()
        roles = (
            VolunteerRole.query.options(joinedload(VolunteerRole.department))
            .order_by(VolunteerRole.name)
            .all()
        )
        if request.method == 'POST':
            role_id = request.form.get('role_id')
            volunteer_id = request.form.get('volunteer_id')
            if not role_id or not volunteer_id:
                flash('Please select both a serving role and a volunteer.', 'danger')
                return render_template(
                    'admin/volunteers/form.html',
                    roles=roles,
                    volunteers=volunteers,
                )
            role = db.session.get(VolunteerRole, int(role_id))
            volunteer = db.session.get(User, int(volunteer_id))
            if not role or not volunteer:
                flash('Invalid role or volunteer selection.', 'danger')
                return render_template(
                    'admin/volunteers/form.html',
                    roles=roles,
                    volunteers=volunteers,
                )
            existing = VolunteerAssignment.query.filter_by(
                role_id=role.id, volunteer_id=volunteer.id
            ).first()
            if existing:
                flash('This volunteer is already assigned to the selected role.', 'warning')
                return redirect(
                    url_for('admin.edit_volunteer_assignment', assignment_id=existing.id)
                )

            assignment = VolunteerAssignment()
            assignment.role = role
            assignment.volunteer = volunteer
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            if start_date:
                assignment.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                assignment.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            assignment.notes = request.form.get('notes')
            db.session.add(assignment)
            db.session.commit()
            flash('Volunteer assignment created successfully.', 'success')
            return redirect(url_for('admin.volunteers'))
        return render_template(
            'admin/volunteers/form.html',
            roles=roles,
            volunteers=volunteers,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error creating assignment: {str(e)}")
        db.session.rollback()
        flash('An error occurred while creating volunteer assignment.', 'danger')
        return redirect(url_for('admin.volunteers'))
    except Exception as e:
        current_app.logger.error(f"Error creating assignment: {str(e)}")
        flash('An error occurred while creating volunteer assignment.', 'danger')
        return redirect(url_for('admin.volunteers'))


@admin_bp.route('/admin/volunteers/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_volunteer_assignment(assignment_id):
    try:
        assignment = VolunteerAssignment.query.get_or_404(assignment_id)
        volunteers = User.query.order_by(User.username).all()
        roles = (
            VolunteerRole.query.options(joinedload(VolunteerRole.department))
            .order_by(VolunteerRole.name)
            .all()
        )
        if request.method == 'POST':
            role_id = request.form.get('role_id')
            volunteer_id = request.form.get('volunteer_id')
            if not role_id or not volunteer_id:
                flash('Please select both a serving role and a volunteer.', 'danger')
                return render_template(
                    'admin/volunteers/form.html',
                    assignment=assignment,
                    roles=roles,
                    volunteers=volunteers,
                )
            role = db.session.get(VolunteerRole, int(role_id))
            volunteer = db.session.get(User, int(volunteer_id))
            if not role or not volunteer:
                flash('Invalid role or volunteer selection.', 'danger')
                return render_template(
                    'admin/volunteers/form.html',
                    assignment=assignment,
                    roles=roles,
                    volunteers=volunteers,
                )
            duplicate = (
                VolunteerAssignment.query.filter(
                    VolunteerAssignment.id != assignment.id,
                    VolunteerAssignment.role_id == role.id,
                    VolunteerAssignment.volunteer_id == volunteer.id,
                )
                .first()
            )
            if duplicate:
                flash('Another assignment already uses this role and volunteer.', 'warning')
                return redirect(
                    url_for('admin.edit_volunteer_assignment', assignment_id=duplicate.id)
                )
            assignment.role = role
            assignment.volunteer = volunteer
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            assignment.start_date = (
                datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
            )
            assignment.end_date = (
                datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
            )
            assignment.notes = request.form.get('notes')
            db.session.commit()
            flash('Volunteer assignment updated successfully.', 'success')
            return redirect(url_for('admin.volunteers'))
        return render_template(
            'admin/volunteers/form.html',
            assignment=assignment,
            roles=roles,
            volunteers=volunteers,
        )
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error updating assignment: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating volunteer assignment.', 'danger')
        return redirect(url_for('admin.volunteers'))
    except Exception as e:
        current_app.logger.error(f"Error updating assignment: {str(e)}")
        flash('An error occurred while updating volunteer assignment.', 'danger')
        return redirect(url_for('admin.volunteers'))


@admin_bp.route('/admin/volunteers/<int:assignment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_volunteer_assignment(assignment_id):
    try:
        assignment = VolunteerAssignment.query.get_or_404(assignment_id)
        db.session.delete(assignment)
        db.session.commit()
        flash('Volunteer assignment deleted successfully.', 'success')
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error deleting assignment: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting volunteer assignment.', 'danger')
    except Exception as e:
        current_app.logger.error(f"Error deleting assignment: {str(e)}")
        flash('An error occurred while deleting volunteer assignment.', 'danger')
    return redirect(url_for('admin.volunteers'))

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
