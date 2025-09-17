"""Administrative views for staff and executives."""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Iterable

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from models import CareInteraction, Member, PrayerRequest, User
from routes.admin_reports import ReportingService
from tasks import trigger_automation


admin_bp = Blueprint('admin', __name__)


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)

    return wrapper


def _parse_timeframe(value: str | None) -> tuple[datetime, datetime]:
    end = datetime.utcnow()
    mapping = {
        '30d': 30,
        '60d': 60,
        '90d': 90,
        '6m': 180,
        '1y': 365,
    }
    days = mapping.get((value or '').lower(), 90)
    start = end - timedelta(days=days)
    return start, end


@admin_bp.route('/admin')
@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    start, end = _parse_timeframe(request.args.get('range'))
    reporting = ReportingService(db.session)

    attendance = reporting.attendance_trends(start, end)
    volunteer_rates = reporting.volunteer_fulfilment(start, end)
    giving = reporting.giving_summary(start, end)
    assimilation = reporting.assimilation_funnel(start, end)
    care_followups = _recent_care_followups(limit=5)

    return render_template(
        'admin/dashboard/index.html',
        filters={'start': start, 'end': end},
        attendance=attendance,
        volunteer_rates=volunteer_rates,
        giving=giving,
        assimilation=assimilation,
        care_followups=care_followups,
    )


def _recent_care_followups(limit: int = 5) -> Iterable[CareInteraction]:
    return (
        CareInteraction.query
        .order_by(CareInteraction.interaction_date.desc())
        .limit(limit)
        .all()
    )


@admin_bp.route('/admin/users')
@login_required
@admin_required
def users() -> str:
    users_list = User.query.order_by(User.username.asc()).all()
    return render_template('admin/users.html', users=users_list)


@admin_bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password')
        is_admin = bool(request.form.get('is_admin'))

        if not all([username, email, password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.create_user'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('admin.create_user'))

        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html')


@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id: int):
    user = User.query.get_or_404(user_id)
    original_admin = user.is_admin

    if request.method == 'POST':
        user.username = (request.form.get('username') or '').strip() or user.username
        user.email = (request.form.get('email') or '').strip() or user.email
        user.is_admin = bool(request.form.get('is_admin'))
        password = request.form.get('password')
        if password:
            user.set_password(password)

        db.session.commit()

        if original_admin != user.is_admin:
            trigger_automation('member_status_changed', {'user_id': user.id, 'is_admin': user.is_admin})

        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_form.html', user=user)


@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id: int) -> Response:
    if current_user.id == user_id:
        flash('You cannot delete your own account.', 'warning')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/users/import', methods=['POST'])
@login_required
@admin_required
def user_import():
    flash('Bulk import is not enabled in this environment. Users were not modified.', 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/prayers')
@login_required
@admin_required
def prayer_requests():
    requests = PrayerRequest.query.order_by(PrayerRequest.created_at.desc()).all()
    return render_template('admin/prayers.html', prayer_requests=requests)


@admin_bp.route('/admin/members')
@login_required
@admin_required
def members():
    members_list = Member.query.order_by(Member.last_name.asc(), Member.first_name.asc()).all()
    return render_template('admin/members/index.html', members=members_list)


@admin_bp.route('/admin/members/<int:member_id>')
@login_required
@admin_required
def member_profile(member_id: int) -> str:
    member = Member.query.get_or_404(member_id)
    interactions = (
        CareInteraction.query
        .filter_by(member_id=member.id)
        .order_by(CareInteraction.interaction_date.desc())
        .all()
    )
    return render_template(
        'admin/members/detail.html',
        member=member,
        interactions=interactions,
    )
