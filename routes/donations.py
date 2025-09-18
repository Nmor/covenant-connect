from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from models import Donation
from app import db
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal, InvalidOperation
import uuid
import json
from datetime import datetime

import requests
from requests.exceptions import RequestException, Timeout

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

        def _update_donation(*, status=None, transaction_id=None, error_message=None, provider_info=None):
            info = dict(donation.payment_info or {})
            if provider_info:
                info.update(provider_info)
                donation.payment_info = info
            if transaction_id:
                donation.transaction_id = str(transaction_id)
            if status:
                donation.status = status
            if error_message is not None:
                donation.error_message = error_message
            donation.updated_at = datetime.utcnow()
            db.session.add(donation)
            db.session.commit()

        def _handle_failure(provider_name, user_message, log_message, provider_info=None):
            try:
                _update_donation(
                    status='failed',
                    error_message=log_message,
                    provider_info=provider_info,
                )
            except Exception as db_error:
                db.session.rollback()
                current_app.logger.error(
                    'Error saving %s failure state: %s', provider_name, db_error
                )
            current_app.logger.error(
                '%s payment initialization failed: %s', provider_name, log_message
            )
            flash(user_message, 'danger')
            return redirect(url_for('donations.donate'))

        # Initialize payment based on the selected method
        if payment_method == 'paystack' and currency == 'NGN':
            try:
                secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
                if not secret_key:
                    return _handle_failure(
                        'Paystack',
                        'Payment processing is temporarily unavailable.',
                        'Paystack secret key not configured.',
                    )

                headers = {
                    'Authorization': f'Bearer {secret_key}',
                    'Content-Type': 'application/json',
                }

                payload = {
                    'amount': int((amount * 100).to_integral_value()),
                    'currency': 'NGN',
                    'email': email,
                    'reference': reference,
                    'callback_url': url_for('donations.payment_callback', _external=True),
                }

                try:
                    response = requests.post(
                        'https://api.paystack.co/transaction/initialize',
                        headers=headers,
                        json=payload,
                        timeout=10,
                    )
                except Timeout:
                    return _handle_failure(
                        'Paystack',
                        'Paystack payment timed out. Please try again later.',
                        'Request to Paystack initialize endpoint timed out.',
                    )
                except RequestException as exc:
                    return _handle_failure(
                        'Paystack',
                        'Unable to initialize Paystack payment. Please try again later.',
                        f'Request to Paystack failed: {exc}',
                    )

                if response.status_code != 200:
                    body = (getattr(response, 'text', '') or '')[:500]
                    return _handle_failure(
                        'Paystack',
                        'Paystack payment initialization failed. Please try again later.',
                        f'Non-200 response ({response.status_code}) from Paystack initialize endpoint: {body}',
                        provider_info={'paystack_error': body},
                    )

                try:
                    response_data = response.json()
                except ValueError:
                    return _handle_failure(
                        'Paystack',
                        'Paystack payment initialization failed. Please try again later.',
                        'Invalid JSON response from Paystack initialize endpoint.',
                    )

                data = response_data.get('data') or {}
                authorization_url = data.get('authorization_url') or response_data.get('authorization_url')
                if not authorization_url:
                    return _handle_failure(
                        'Paystack',
                        'Paystack payment initialization failed. Please try again later.',
                        'Missing authorization URL in Paystack response.',
                        provider_info={'provider_response': data},
                    )

                transaction_id = data.get('reference') or data.get('id') or response_data.get('reference')
                provider_info = {
                    'authorization_url': authorization_url,
                    'provider_response': data,
                }

                try:
                    _update_donation(
                        transaction_id=transaction_id,
                        provider_info=provider_info,
                    )
                except Exception as db_error:
                    db.session.rollback()
                    current_app.logger.error('Error saving Paystack response: %s', db_error)
                    flash('Payment initialization failed. Please try again later.', 'danger')
                    return redirect(url_for('donations.donate'))

                return redirect(authorization_url)

            except Exception as e:
                current_app.logger.exception("Paystack payment initialization error: %s", e)
                db.session.rollback()
                return _handle_failure(
                    'Paystack',
                    'Payment initialization failed. Please try again later.',
                    f'Unexpected Paystack initialization error: {e}',
                    provider_info={'paystack_exception': str(e)},
                )

        elif payment_method == 'fincra':
            try:
                secret_key = current_app.config.get('FINCRA_SECRET_KEY')
                if not secret_key:
                    return _handle_failure(
                        'Fincra',
                        'Payment processing is temporarily unavailable.',
                        'Fincra secret key not configured.',
                    )

                headers = {
                    'api-key': secret_key,
                    'Content-Type': 'application/json',
                }

                payload = {
                    'amount': str(amount),
                    'currency': currency,
                    'email': email,
                    'reference': reference,
                    'customer': {
                        'firstName': payment_info['first_name'],
                        'lastName': payment_info['last_name'],
                        'email': email,
                    },
                    'redirectUrl': url_for('donations.payment_callback', _external=True),
                    'paymentType': 'card',
                }

                try:
                    response = requests.post(
                        'https://api.fincra.com/checkout/payments',
                        headers=headers,
                        json=payload,
                        timeout=10,
                    )
                except Timeout:
                    return _handle_failure(
                        'Fincra',
                        'Fincra payment timed out. Please try again later.',
                        'Request to Fincra initialize endpoint timed out.',
                    )
                except RequestException as exc:
                    return _handle_failure(
                        'Fincra',
                        'Unable to initialize Fincra payment. Please try again later.',
                        f'Request to Fincra failed: {exc}',
                    )

                if response.status_code != 200:
                    body = (getattr(response, 'text', '') or '')[:500]
                    return _handle_failure(
                        'Fincra',
                        'Fincra payment initialization failed. Please try again later.',
                        f'Non-200 response ({response.status_code}) from Fincra initialize endpoint: {body}',
                        provider_info={'fincra_error': body},
                    )

                try:
                    response_data = response.json()
                except ValueError:
                    return _handle_failure(
                        'Fincra',
                        'Fincra payment initialization failed. Please try again later.',
                        'Invalid JSON response from Fincra initialize endpoint.',
                    )

                data = response_data.get('data') or {}
                authorization_url = (
                    data.get('checkoutUrl')
                    or data.get('checkout_url')
                    or data.get('paymentLink')
                    or data.get('link')
                )
                if not authorization_url:
                    return _handle_failure(
                        'Fincra',
                        'Fincra payment initialization failed. Please try again later.',
                        'Missing checkout URL in Fincra response.',
                        provider_info={'provider_response': data},
                    )

                transaction_id = (
                    data.get('transactionReference')
                    or data.get('reference')
                    or data.get('id')
                )
                provider_info = {
                    'authorization_url': authorization_url,
                    'provider_response': data,
                }

                try:
                    _update_donation(
                        transaction_id=transaction_id,
                        provider_info=provider_info,
                    )
                except Exception as db_error:
                    db.session.rollback()
                    current_app.logger.error('Error saving Fincra response: %s', db_error)
                    flash('Payment initialization failed. Please try again later.', 'danger')
                    return redirect(url_for('donations.donate'))

                return redirect(authorization_url)

            except Exception as e:
                current_app.logger.exception("Fincra payment initialization error: %s", e)
                db.session.rollback()
                return _handle_failure(
                    'Fincra',
                    'Payment initialization failed. Please try again later.',
                    f'Unexpected Fincra initialization error: {e}',
                    provider_info={'fincra_exception': str(e)},
                )

        elif payment_method == 'stripe':
            try:
                secret_key = current_app.config.get('STRIPE_SECRET_KEY')
                if not secret_key:
                    return _handle_failure(
                        'Stripe',
                        'Payment processing is temporarily unavailable.',
                        'Stripe secret key not configured.',
                    )

                headers = {
                    'Authorization': f'Bearer {secret_key}',
                }

                payload = {
                    'mode': 'payment',
                    'success_url': url_for(
                        'donations.payment_callback', _external=True
                    )
                    + f'?status=successful&reference={reference}',
                    'cancel_url': url_for('donations.donate', _external=True),
                    'line_items[0][price_data][currency]': currency.lower(),
                    'line_items[0][price_data][product_data][name]': 'Donation',
                    'line_items[0][price_data][unit_amount]': int(
                        (amount * 100).to_integral_value()
                    ),
                    'line_items[0][quantity]': 1,
                    'customer_email': email,
                }

                try:
                    response = requests.post(
                        'https://api.stripe.com/v1/checkout/sessions',
                        headers=headers,
                        data=payload,
                        timeout=10,
                    )
                except Timeout:
                    return _handle_failure(
                        'Stripe',
                        'Stripe payment timed out. Please try again later.',
                        'Request to Stripe initialize endpoint timed out.',
                    )
                except RequestException as exc:
                    return _handle_failure(
                        'Stripe',
                        'Unable to initialize Stripe payment. Please try again later.',
                        f'Request to Stripe failed: {exc}',
                    )

                if response.status_code != 200:
                    body = (getattr(response, 'text', '') or '')[:500]
                    return _handle_failure(
                        'Stripe',
                        'Stripe payment initialization failed. Please try again later.',
                        f'Non-200 response ({response.status_code}) from Stripe initialize endpoint: {body}',
                        provider_info={'stripe_error': body},
                    )

                try:
                    response_data = response.json()
                except ValueError:
                    return _handle_failure(
                        'Stripe',
                        'Stripe payment initialization failed. Please try again later.',
                        'Invalid JSON response from Stripe initialize endpoint.',
                    )

                authorization_url = response_data.get('url')
                if not authorization_url:
                    return _handle_failure(
                        'Stripe',
                        'Stripe payment initialization failed. Please try again later.',
                        'Missing checkout URL in Stripe response.',
                        provider_info={'provider_response': response_data},
                    )

                transaction_id = response_data.get('id')
                provider_info = {
                    'authorization_url': authorization_url,
                    'provider_response': response_data,
                }

                try:
                    _update_donation(
                        transaction_id=transaction_id,
                        provider_info=provider_info,
                    )
                except Exception as db_error:
                    db.session.rollback()
                    current_app.logger.error('Error saving Stripe response: %s', db_error)
                    flash('Payment initialization failed. Please try again later.', 'danger')
                    return redirect(url_for('donations.donate'))

                return redirect(authorization_url)

            except Exception as e:
                current_app.logger.exception("Stripe payment initialization error: %s", e)
                db.session.rollback()
                return _handle_failure(
                    'Stripe',
                    'Payment initialization failed. Please try again later.',
                    f'Unexpected Stripe initialization error: {e}',
                    provider_info={'stripe_exception': str(e)},
                )

        elif payment_method == 'flutterwave':
            try:
                secret_key = current_app.config.get('FLUTTERWAVE_SECRET_KEY')
                if not secret_key:
                    return _handle_failure(
                        'Flutterwave',
                        'Payment processing is temporarily unavailable.',
                        'Flutterwave secret key not configured.',
                    )

                headers = {
                    'Authorization': f'Bearer {secret_key}',
                    'Content-Type': 'application/json',
                }

                payload = {
                    'tx_ref': reference,
                    'amount': str(amount),
                    'currency': currency,
                    'redirect_url': url_for('donations.payment_callback', _external=True),
                    'customer': {
                        'email': email,
                    },
                    'payment_options': 'card',
                }

                try:
                    response = requests.post(
                        'https://api.flutterwave.com/v3/payments',
                        headers=headers,
                        json=payload,
                        timeout=10,
                    )
                except Timeout:
                    return _handle_failure(
                        'Flutterwave',
                        'Flutterwave payment timed out. Please try again later.',
                        'Request to Flutterwave initialize endpoint timed out.',
                    )
                except RequestException as exc:
                    return _handle_failure(
                        'Flutterwave',
                        'Unable to initialize Flutterwave payment. Please try again later.',
                        f'Request to Flutterwave failed: {exc}',
                    )

                if response.status_code != 200:
                    body = (getattr(response, 'text', '') or '')[:500]
                    return _handle_failure(
                        'Flutterwave',
                        'Flutterwave payment initialization failed. Please try again later.',
                        f'Non-200 response ({response.status_code}) from Flutterwave initialize endpoint: {body}',
                        provider_info={'flutterwave_error': body},
                    )

                try:
                    response_data = response.json()
                except ValueError:
                    return _handle_failure(
                        'Flutterwave',
                        'Flutterwave payment initialization failed. Please try again later.',
                        'Invalid JSON response from Flutterwave initialize endpoint.',
                    )

                data = response_data.get('data') or {}
                authorization_url = data.get('link') or data.get('url')
                if not authorization_url:
                    return _handle_failure(
                        'Flutterwave',
                        'Flutterwave payment initialization failed. Please try again later.',
                        'Missing checkout URL in Flutterwave response.',
                        provider_info={'provider_response': data},
                    )

                transaction_id = data.get('id') or data.get('flw_ref') or data.get('tx_ref')
                provider_info = {
                    'authorization_url': authorization_url,
                    'provider_response': data,
                }

                try:
                    _update_donation(
                        transaction_id=transaction_id,
                        provider_info=provider_info,
                    )
                except Exception as db_error:
                    db.session.rollback()
                    current_app.logger.error('Error saving Flutterwave response: %s', db_error)
                    flash('Payment initialization failed. Please try again later.', 'danger')
                    return redirect(url_for('donations.donate'))

                return redirect(authorization_url)

            except Exception as e:
                current_app.logger.exception("Flutterwave payment initialization error: %s", e)
                db.session.rollback()
                return _handle_failure(
                    'Flutterwave',
                    'Payment initialization failed. Please try again later.',
                    f'Unexpected Flutterwave initialization error: {e}',
                    provider_info={'flutterwave_exception': str(e)},
                )

        else:
            return _handle_failure(
                'Donation',
                'Invalid payment method or currency combination.',
                f'Unsupported payment method "{payment_method}" with currency "{currency}".',
            )

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
