import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import Donation

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
            amount = Decimal(amount)
            if amount <= 0:
                raise InvalidOperation("Amount must be positive")
        except (InvalidOperation, ValueError):
            flash('Please enter a valid donation amount.', 'danger')
            return redirect(url_for('donations.donate'))

        # Create donation record
        payment_info = {}
        if payment_method == 'fincra':
            required_fields = ['first_name', 'last_name', 'country']
            if not all(request.form.get(field) for field in required_fields):
                flash('Please fill in all required fields for international payment.', 'warning')
                return redirect(url_for('donations.donate'))
            
            payment_info = {
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'country': request.form.get('country')
            }

        # Generate unique reference
        reference = str(uuid.uuid4())

        # Create donation record
        donation = Donation(
            email=email,
            amount=amount,
            currency=currency,
            reference=reference,
            status='pending',
            payment_method=payment_method,
            payment_info=payment_info
        )

        db.session.add(donation)
        db.session.commit()

        # Initialize payment based on the selected method
        if payment_method == 'paystack' and currency == 'NGN':
            try:
                # Initialize Paystack payment
                secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
                if not secret_key:
                    flash('Payment processing is temporarily unavailable.', 'danger')
                    current_app.logger.error("Paystack secret key not configured")
                    return redirect(url_for('donations.donate'))

                payload = {
                    'amount': int((amount * 100).to_integral_value()),  # Paystack expects amount in kobo
                    'currency': 'NGN',
                    'email': email,
                    'reference': reference,
                    'callback_url': url_for('donations.payment_callback', _external=True)
                }

                current_app.logger.debug('Prepared Paystack payload: %s', payload)

                # TODO: Make API call to Paystack to initialize payment
                # For now, we'll simulate success
                flash('Payment initialization successful!', 'success')
                return redirect(url_for('donations.donate'))

            except Exception as e:
                current_app.logger.error(f"Paystack payment initialization error: {str(e)}")
                flash('Payment initialization failed. Please try again later.', 'danger')
                return redirect(url_for('donations.donate'))

        elif payment_method == 'fincra':
            try:
                secret_key = current_app.config.get('FINCRA_SECRET_KEY')
                if not secret_key:
                    flash('Payment processing is temporarily unavailable.', 'danger')
                    current_app.logger.error("Fincra secret key not configured")
                    return redirect(url_for('donations.donate'))

                # Compose a structured request payload when the integration is activated.
                redirect_url = url_for('donations.payment_callback', _external=True)
                fincra_payload = {
                    'amount': str(amount),
                    'currency': currency,
                    'email': email,
                    'reference': reference,
                    'customer': {
                        'firstName': payment_info['first_name'],
                        'lastName': payment_info['last_name'],
                        'email': email,
                    },
                    'redirectUrl': redirect_url,
                    'paymentType': 'card',
                }
                current_app.logger.debug('Prepared Fincra payload: %s', fincra_payload)

                # TODO: Make API call to Fincra to initialize payment
                # For now, we'll simulate success
                flash('Payment initialization successful!', 'success')
                return redirect(url_for('donations.donate'))

            except Exception as e:
                current_app.logger.error(f"Fincra payment initialization error: {str(e)}")
                flash('Payment initialization failed. Please try again later.', 'danger')
                return redirect(url_for('donations.donate'))
        elif payment_method == 'stripe':
            try:
                secret_key = current_app.config.get('STRIPE_SECRET_KEY')
                if not secret_key:
                    flash('Payment processing is temporarily unavailable.', 'danger')
                    current_app.logger.error("Stripe secret key not configured")
                    return redirect(url_for('donations.donate'))

                # TODO: Make API call to Stripe to initialize payment
                flash('Payment initialization successful!', 'success')
                return redirect(url_for('donations.donate'))

            except Exception as e:
                current_app.logger.error(f"Stripe payment initialization error: {str(e)}")
                flash('Payment initialization failed. Please try again later.', 'danger')
                return redirect(url_for('donations.donate'))

        elif payment_method == 'flutterwave':
            try:
                secret_key = current_app.config.get('FLUTTERWAVE_SECRET_KEY')
                if not secret_key:
                    flash('Payment processing is temporarily unavailable.', 'danger')
                    current_app.logger.error("Flutterwave secret key not configured")
                    return redirect(url_for('donations.donate'))

                # TODO: Make API call to Flutterwave to initialize payment
                flash('Payment initialization successful!', 'success')
                return redirect(url_for('donations.donate'))

            except Exception as e:
                current_app.logger.error(f"Flutterwave payment initialization error: {str(e)}")
                flash('Payment initialization failed. Please try again later.', 'danger')
                return redirect(url_for('donations.donate'))

        else:
            flash('Invalid payment method or currency combination.', 'danger')
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
        db.session.rollback()
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
    """Handle payment callback from payment providers"""
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
