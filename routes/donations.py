from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from models import Donation
from app import db
from sqlalchemy.exc import SQLAlchemyError
import uuid

donations_bp = Blueprint('donations', __name__)

@donations_bp.route('/donate', methods=['GET'])
def donate():
    try:
        return render_template('donations.html')
    except Exception as e:
        current_app.logger.error(f"Error rendering donation page: {str(e)}")
        flash('Unable to load the donation page. Please try again later.', 'danger')
        return redirect(url_for('home.home'))

@donations_bp.route('/donate/process', methods=['POST'])
def process_donation():
    try:
        email = request.form.get('email')
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method')

        if not all([email, amount, payment_method]):
            flash('Please fill in all required fields.', 'warning')
            return redirect(url_for('donations.donate'))

        # Create donation record
        donation = Donation(
            email=email,
            amount=float(amount),
            reference=str(uuid.uuid4()),
            status='pending'
        )
        db.session.add(donation)
        db.session.commit()

        # TODO: Integrate with payment gateways
        if payment_method == 'paystack':
            # Placeholder for Paystack integration
            flash('Paystack integration coming soon!', 'info')
        else:
            # Placeholder for Fincra integration
            flash('Fincra integration coming soon!', 'info')

        return redirect(url_for('donations.donate'))

    except ValueError:
        flash('Please enter a valid donation amount.', 'danger')
        return redirect(url_for('donations.donate'))
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in donation processing: {str(e)}")
        db.session.rollback()
        flash('Unable to process donation. Please try again later.', 'danger')
        return redirect(url_for('donations.donate'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error in donation processing: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'danger')
        return redirect(url_for('donations.donate'))
