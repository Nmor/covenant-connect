from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from models import Donation
from app import db
from sqlalchemy.exc import SQLAlchemyError
import uuid
import json
from datetime import datetime
import os

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
        currency = request.form.get('currency', 'USD')
        payment_method = request.form.get('payment_method')

        if not all([email, amount, payment_method]):
            flash('Please fill in all required fields.', 'warning')
            return redirect(url_for('donations.donate'))

        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            flash('Please enter a valid donation amount.', 'danger')
            return redirect(url_for('donations.donate'))

        # Create donation record
        payment_metadata = {}
        if payment_method == 'fincra':
            required_fields = ['first_name', 'last_name', 'country']
            if not all(request.form.get(field) for field in required_fields):
                flash('Please fill in all required fields for international payment.', 'warning')
                return redirect(url_for('donations.donate'))
            
            payment_metadata = {
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'country': request.form.get('country')
            }

        # Generate unique reference
        reference = str(uuid.uuid4())

        donation = Donation(
            email=email,
            amount=amount,
            currency=currency,
            reference=reference,
            status='pending',
            payment_method=payment_method,
            payment_metadata=payment_metadata
        )
        db.session.add(donation)
        db.session.commit()

        # Initialize payment based on the selected method
        if payment_method == 'fincra':
            # Initialize Fincra payment
            try:
                headers = {
                    'api-key': os.environ['FINCRA_SECRET_KEY'],
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'amount': str(amount),
                    'currency': currency,
                    'email': email,
                    'reference': reference,
                    'customer': {
                        'firstName': payment_metadata['first_name'],
                        'lastName': payment_metadata['last_name'],
                        'email': email
                    },
                    'redirectUrl': url_for('donations.payment_callback', _external=True),
                    'paymentType': 'card'
                }

                # TODO: Make API call to Fincra to initialize payment
                # For now, we'll simulate success
                flash('Payment initialization successful!', 'success')
                return redirect(url_for('donations.donate'))

            except KeyError:
                flash('Payment initialization failed. Please try again later.', 'danger')
                return redirect(url_for('donations.donate'))
        else:
            # Placeholder for Paystack integration
            flash('Paystack integration coming soon!', 'info')
            return redirect(url_for('donations.donate'))

    except ValueError as e:
        flash(str(e), 'danger')
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

@donations_bp.route('/webhooks/fincra', methods=['POST'])
def fincra_webhook():
    """Handle Fincra payment webhooks"""
    try:
        # Verify webhook signature
        signature = request.headers.get('x-fincra-signature')
        if not signature:
            current_app.logger.error("Missing webhook signature")
            return jsonify({'status': 'error', 'message': 'Missing signature'}), 401

        payload = request.get_json()
        if not payload:
            current_app.logger.error("Invalid webhook payload")
            return jsonify({'status': 'error', 'message': 'Invalid payload'}), 400

        # Extract transaction details
        transaction_id = payload.get('transactionId')
        status = payload.get('status')
        reference = payload.get('reference')

        if not all([transaction_id, status, reference]):
            current_app.logger.error("Missing required webhook data")
            return jsonify({'status': 'error', 'message': 'Missing required data'}), 400

        # Update donation record
        donation = Donation.query.filter_by(reference=reference).first()
        if not donation:
            current_app.logger.error(f"Donation not found for reference: {reference}")
            return jsonify({'status': 'error', 'message': 'Donation not found'}), 404

        # Update donation status
        donation.transaction_id = transaction_id
        donation.status = 'success' if status.lower() == 'successful' else 'failed'
        donation.error_message = payload.get('failureReason')
        donation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        current_app.logger.error(f"Error processing Fincra webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@donations_bp.route('/payment/callback')
def payment_callback():
    """Handle payment callback from Fincra"""
    try:
        status = request.args.get('status')
        reference = request.args.get('reference')
        
        if status and reference:
            donation = Donation.query.filter_by(reference=reference).first()
            if donation:
                if status.lower() == 'successful':
                    flash('Payment successful! Thank you for your donation.', 'success')
                else:
                    flash('Payment failed. Please try again.', 'danger')
                
        return redirect(url_for('donations.donate'))
    except Exception as e:
        current_app.logger.error(f"Error processing payment callback: {str(e)}")
        flash('Error processing payment. Please contact support.', 'danger')
        return redirect(url_for('donations.donate'))
