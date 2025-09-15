from decimal import Decimal
import re
from models import Donation


def get_token(client, path):
    resp = client.get(path)
    token = re.search("name='csrf_token' value='([^']+)'", resp.data.decode()).group(1)
    return token


def test_donation_rejects_invalid_amount(client):
    token = get_token(client, '/donate')
    resp = client.post('/donate/process', data={
        'csrf_token': token,
        'email': 'test@example.com',
        'amount': 'abc',
        'payment_method': 'paystack'
    }, follow_redirects=True)
    assert b'valid donation amount' in resp.data.lower()


def test_donation_stores_decimal(client, app):
    token = get_token(client, '/donate')
    resp = client.post('/donate/process', data={
        'csrf_token': token,
        'email': 'user@example.com',
        'amount': '10.50',
        'payment_method': 'paystack',
        'currency': 'NGN'
    }, follow_redirects=True)
    with app.app_context():
        donation = Donation.query.filter_by(email='user@example.com').first()
        assert donation is not None
        assert donation.amount == Decimal('10.50')
