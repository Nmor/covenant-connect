import re

from app import db
from models import User


def get_token(client, path):
    resp = client.get(path)
    token = re.search("name='csrf_token' value='([^']+)'", resp.data.decode()).group(1)
    return token


def test_dashboard_requires_login(client):
    resp = client.get('/dashboard')
    assert resp.status_code == 302


def test_dashboard_access_after_login(client, app):
    with app.app_context():
        user = User(username='dash', email='dash@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    token = get_token(client, '/login')
    client.post('/login', data={
        'csrf_token': token,
        'email': 'dash@example.com',
        'password': 'password'
    }, follow_redirects=True)
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    assert b'Internal Dashboard' in resp.data
