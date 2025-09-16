from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from models import User, Donation, PrayerRequest, Event, Church
from app import db

internal_bp = Blueprint('internal', __name__)

@internal_bp.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'users': User.query.count(),
        'donations': Donation.query.count(),
        'prayers': PrayerRequest.query.count(),
        'events': Event.query.count()
    }
    return render_template('internal/dashboard.html', stats=stats)


@internal_bp.route('/churches')
@login_required
def list_churches():
    churches = Church.query.all()
    return render_template('internal/churches.html', churches=churches)


@internal_bp.route('/churches/add', methods=['GET', 'POST'])
@login_required
def add_church():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form.get('address')
        church = Church(name=name, address=address)
        db.session.add(church)
        db.session.commit()
        return redirect(url_for('internal.list_churches'))
    return render_template('internal/church_form.html')


@internal_bp.route('/churches/<int:church_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_church(church_id):
    church = Church.query.get_or_404(church_id)
    if request.method == 'POST':
        church.name = request.form['name']
        church.address = request.form.get('address')
        db.session.commit()
        return redirect(url_for('internal.list_churches'))
    return render_template('internal/church_form.html', church=church)


@internal_bp.route('/churches/<int:church_id>/delete', methods=['POST'])
@login_required
def delete_church(church_id):
    church = Church.query.get_or_404(church_id)
    db.session.delete(church)
    db.session.commit()
    return redirect(url_for('internal.list_churches'))
