import json
from decimal import Decimal
import re

from requests.exceptions import RequestException, Timeout

from models import Donation


def get_token(client, path):
    resp = client.get(path)
    token = re.search("name='csrf_token' value='([^']+)'", resp.data.decode()).group(1)
    return token


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        if isinstance(payload, dict):
            self.text = json.dumps(payload)
        else:
            self.text = '' if payload is None else str(payload)

    def json(self):
        if isinstance(self._payload, dict):
            return self._payload
        raise ValueError('No JSON payload configured')


def test_donation_rejects_invalid_amount(client):
    token = get_token(client, '/donate')
    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'test@example.com',
            'amount': 'abc',
            'payment_method': 'paystack',
        },
        follow_redirects=True,
    )
    assert b'valid donation amount' in resp.data.lower()


def test_paystack_success_redirects_to_authorization_url(monkeypatch, client, app):
    token = get_token(client, '/donate')
    captured = {}

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['json'] = json
        captured['data'] = data
        captured['timeout'] = timeout
        return DummyResponse(
            200,
            {
                'data': {
                    'authorization_url': 'https://paystack.test/redirect',
                    'reference': 'ref-123',
                }
            },
        )

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'paystack-success@example.com',
            'amount': '50.00',
            'currency': 'NGN',
            'payment_method': 'paystack',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == 'https://paystack.test/redirect'
    assert captured['url'].endswith('/transaction/initialize')
    assert captured['headers']['Authorization'] == 'Bearer test-paystack'
    assert captured['json']['amount'] == 5000
    assert captured['timeout'] == 10

    with app.app_context():
        donation = Donation.query.filter_by(email='paystack-success@example.com').first()
        assert donation is not None
        assert donation.amount == Decimal('50.00')
        assert donation.transaction_id == 'ref-123'
        assert donation.payment_info['authorization_url'] == 'https://paystack.test/redirect'
        assert donation.payment_info['provider_response']['reference'] == 'ref-123'
        assert donation.status == 'pending'


def test_paystack_failure_marks_donation_failed(monkeypatch, client, app):
    token = get_token(client, '/donate')

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        return DummyResponse(400, {'status': False, 'message': 'Invalid data'})

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'paystack-failure@example.com',
            'amount': '20.00',
            'currency': 'NGN',
            'payment_method': 'paystack',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/donate'

    with app.app_context():
        donation = Donation.query.filter_by(email='paystack-failure@example.com').first()
        assert donation is not None
        assert donation.status == 'failed'
        assert 'Non-200 response (400)' in donation.error_message
        assert donation.transaction_id is None
        assert 'paystack_error' in donation.payment_info


def test_fincra_success_redirects_to_checkout(monkeypatch, client, app):
    token = get_token(client, '/donate')
    captured = {}

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['json'] = json
        captured['timeout'] = timeout
        return DummyResponse(
            200,
            {
                'data': {
                    'checkoutUrl': 'https://fincra.test/checkout',
                    'transactionReference': 'txn-789',
                }
            },
        )

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'fincra-success@example.com',
            'amount': '75.00',
            'currency': 'USD',
            'payment_method': 'fincra',
            'first_name': 'Ada',
            'last_name': 'Lovelace',
            'country': 'GB',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == 'https://fincra.test/checkout'
    assert captured['json']['customer']['firstName'] == 'Ada'
    assert captured['timeout'] == 10

    with app.app_context():
        donation = Donation.query.filter_by(email='fincra-success@example.com').first()
        assert donation is not None
        assert donation.transaction_id == 'txn-789'
        assert donation.payment_info['first_name'] == 'Ada'
        assert donation.payment_info['authorization_url'] == 'https://fincra.test/checkout'
        assert donation.payment_info['provider_response']['transactionReference'] == 'txn-789'
        assert donation.status == 'pending'


def test_fincra_timeout_marks_failed(monkeypatch, client, app):
    token = get_token(client, '/donate')

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        raise Timeout('timed out')

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'fincra-timeout@example.com',
            'amount': '40.00',
            'currency': 'USD',
            'payment_method': 'fincra',
            'first_name': 'Ada',
            'last_name': 'Lovelace',
            'country': 'GB',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/donate'

    with app.app_context():
        donation = Donation.query.filter_by(email='fincra-timeout@example.com').first()
        assert donation is not None
        assert donation.status == 'failed'
        assert donation.error_message == 'Request to Fincra initialize endpoint timed out.'
        assert donation.payment_info['first_name'] == 'Ada'
        assert donation.transaction_id is None


def test_stripe_success_redirects_to_checkout(monkeypatch, client, app):
    token = get_token(client, '/donate')
    captured = {}

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['json'] = json
        captured['data'] = data
        captured['timeout'] = timeout
        return DummyResponse(200, {'url': 'https://stripe.test/session', 'id': 'cs_test'})

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'stripe-success@example.com',
            'amount': '15.00',
            'currency': 'USD',
            'payment_method': 'stripe',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == 'https://stripe.test/session'
    assert captured['timeout'] == 10
    assert captured['data']['line_items[0][price_data][currency]'] == 'usd'

    with app.app_context():
        donation = Donation.query.filter_by(email='stripe-success@example.com').first()
        assert donation is not None
        assert donation.transaction_id == 'cs_test'
        assert donation.payment_info['authorization_url'] == 'https://stripe.test/session'
        assert donation.payment_info['provider_response']['id'] == 'cs_test'
        assert donation.status == 'pending'


def test_stripe_failure_marks_donation_failed(monkeypatch, client, app):
    token = get_token(client, '/donate')

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        return DummyResponse(500, {'error': 'server'})

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'stripe-failure@example.com',
            'amount': '25.00',
            'currency': 'USD',
            'payment_method': 'stripe',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/donate'

    with app.app_context():
        donation = Donation.query.filter_by(email='stripe-failure@example.com').first()
        assert donation is not None
        assert donation.status == 'failed'
        assert 'Non-200 response (500)' in donation.error_message
        assert donation.transaction_id is None
        assert 'stripe_error' in donation.payment_info


def test_flutterwave_success_redirects_to_checkout(monkeypatch, client, app):
    token = get_token(client, '/donate')
    captured = {}

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        captured['url'] = url
        captured['headers'] = headers
        captured['json'] = json
        captured['timeout'] = timeout
        return DummyResponse(
            200,
            {
                'data': {
                    'link': 'https://flutterwave.test/pay',
                    'id': 'flw-456',
                }
            },
        )

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'flutterwave-success@example.com',
            'amount': '35.00',
            'currency': 'USD',
            'payment_method': 'flutterwave',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == 'https://flutterwave.test/pay'
    assert captured['json']['payment_options'] == 'card'
    assert captured['timeout'] == 10

    with app.app_context():
        donation = Donation.query.filter_by(email='flutterwave-success@example.com').first()
        assert donation is not None
        assert donation.transaction_id == 'flw-456'
        assert donation.payment_info['authorization_url'] == 'https://flutterwave.test/pay'
        assert donation.payment_info['provider_response']['id'] == 'flw-456'
        assert donation.status == 'pending'


def test_flutterwave_request_exception_marks_failed(monkeypatch, client, app):
    token = get_token(client, '/donate')

    def mock_post(url, headers=None, json=None, data=None, timeout=None):
        raise RequestException('boom')

    monkeypatch.setattr('routes.donations.requests.post', mock_post)

    resp = client.post(
        '/donate/process',
        data={
            'csrf_token': token,
            'email': 'flutterwave-failure@example.com',
            'amount': '45.00',
            'currency': 'USD',
            'payment_method': 'flutterwave',
        },
    )

    assert resp.status_code == 302
    assert resp.headers['Location'] == '/donate'

    with app.app_context():
        donation = Donation.query.filter_by(email='flutterwave-failure@example.com').first()
        assert donation is not None
        assert donation.status == 'failed'
        assert 'Request to Flutterwave failed: boom' in donation.error_message
        assert donation.transaction_id is None
