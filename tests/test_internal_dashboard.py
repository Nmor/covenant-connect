import re

from app import db
from models import ServiceIntegration, User


def get_token(client, path: str) -> str:
    response = client.get(path, follow_redirects=True)
    match = re.search(r"name=['\"]csrf_token['\"] value=['\"]([^'\"]+)['\"]", response.data.decode())
    assert match, f"CSRF token not found in response for {path}"
    return match.group(1)


def login(client, email: str, password: str) -> None:
    token = get_token(client, '/login')
    client.post(
        '/login',
        data={
            'csrf_token': token,
            'email': email,
            'password': password,
        },
        follow_redirects=True,
    )


def test_dashboard_requires_login(client):
    resp = client.get('/dashboard')
    assert resp.status_code == 302


def test_dashboard_access_after_login(client, app):
    with app.app_context():
        user = User(username='dash', email='dash@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    login(client, 'dash@example.com', 'password')
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    assert b'Internal Dashboard' in resp.data


def test_integrations_view_requires_admin(client, app):
    with app.app_context():
        user = User(username='staff', email='staff@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    login(client, 'staff@example.com', 'password')
    resp = client.get('/integrations')
    assert resp.status_code == 403


def test_admin_can_update_mailgun_settings(client, app):
    with app.app_context():
        admin = User(username='root', email='admin@example.com', is_admin=True)
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()

    login(client, 'admin@example.com', 'password')
    token = get_token(client, '/integrations')
    response = client.post(
        '/integrations',
        data={
            'csrf_token': token,
            'provider': 'mailgun',
            'sender_email': 'noreply@example.com',
            'domain': 'mg.example.com',
            'api_key': 'key-test',
            'base_url': 'https://api.mailgun.net/v3',
            'is_active': 'on',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        integration = ServiceIntegration.query.filter_by(service='email', provider='mailgun').one()
        assert integration.is_active is True
        assert integration.config['domain'] == 'mg.example.com'
        assert integration.config['api_key'] == 'key-test'
        others = ServiceIntegration.query.filter(
            ServiceIntegration.service == 'email',
            ServiceIntegration.provider != 'mailgun',
        ).all()
        assert all(not other.is_active for other in others)


def test_sensitive_fields_remain_when_blank(client, app):
    with app.app_context():
        admin = User(username='secret-admin', email='secret@example.com', is_admin=True)
        admin.set_password('password')
        db.session.add(admin)
        integration = ServiceIntegration(
            service='email',
            provider='mailgun',
            display_name='Mailgun',
            config={'api_key': 'existing-secret', 'domain': 'mg.example.com'},
            is_active=False,
        )
        db.session.add(integration)
        db.session.commit()

    login(client, 'secret@example.com', 'password')
    token = get_token(client, '/integrations')
    client.post(
        '/integrations',
        data={
            'csrf_token': token,
            'provider': 'mailgun',
            'sender_email': 'alerts@example.com',
            'domain': 'mg.example.com',
            'api_key': '',
            'base_url': 'https://api.mailgun.net/v3',
        },
        follow_redirects=True,
    )

    with app.app_context():
        integration = ServiceIntegration.query.filter_by(service='email', provider='mailgun').one()
        assert integration.config['api_key'] == 'existing-secret'
