from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from models import Donation

donations_bp = Blueprint('donations', __name__)


@donations_bp.route('/donate', methods=['GET'])
def donate():
    return render_template('donations.html')


@donations_bp.route('/donate/process', methods=['POST'])
def process_donation():
    email = (request.form.get('email') or '').strip()
    amount_raw = (request.form.get('amount') or '').strip()
    payment_method = (request.form.get('payment_method') or '').strip()
    currency = (request.form.get('currency') or 'USD').strip() or 'USD'

    if not email or not amount_raw or not payment_method:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('donations.donate'))

    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        flash('Please enter a valid donation amount.', 'danger')
        return redirect(url_for('donations.donate'))

    donation = Donation(
        email=email,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        reference=str(uuid.uuid4()),
        status='received',
    )
    db.session.add(donation)
    db.session.commit()

    flash('Thank you for your donation!', 'success')
    return redirect(url_for('donations.donate'))
