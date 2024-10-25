from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app import db
from models import PrayerRequest

prayers_bp = Blueprint('prayers', __name__)

@prayers_bp.route('/prayers', methods=['GET'])
def prayers():
    public_prayers = PrayerRequest.query.filter_by(is_public=True).order_by(PrayerRequest.created_at.desc()).all()
    return render_template('prayers.html', prayers=public_prayers)

@prayers_bp.route('/prayers/submit', methods=['POST'])
def submit_prayer():
    name = request.form.get('name')
    email = request.form.get('email')
    prayer_request = request.form.get('request')
    is_public = bool(request.form.get('is_public'))

    if not all([name, email, prayer_request]):
        flash('Please fill all required fields', 'error')
        return redirect(url_for('prayers.prayers'))

    new_prayer = PrayerRequest(
        name=name,
        email=email,
        request=prayer_request,
        is_public=is_public
    )
    
    db.session.add(new_prayer)
    db.session.commit()
    
    flash('Prayer request submitted successfully', 'success')
    return redirect(url_for('prayers.prayers'))
