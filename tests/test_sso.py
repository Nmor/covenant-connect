import base64
import json
from urllib.parse import parse_qs, urlparse

from app import db
from integrations.sso import get_enabled_sso_providers
from models import User


class DummyResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code
        self.text = json.dumps(self._json)

    def json(self):
        return self._json


def _build_id_token(payload):
    header_segment = base64.urlsafe_b64encode(json.dumps({'alg': 'none'}).encode()).decode().rstrip('=')
    payload_segment = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    return f"{header_segment}.{payload_segment}."


def test_enabled_sso_providers_empty(app):
    providers = get_enabled_sso_providers(app.config)
    assert providers == []


def test_enabled_sso_providers_detects_google(app):
    app.config.update({'GOOGLE_CLIENT_ID': 'client', 'GOOGLE_CLIENT_SECRET': 'secret'})
    providers = get_enabled_sso_providers(app.config)
    assert any(provider.name == 'google' for provider in providers)


def test_google_oauth_flow_creates_user(client, app, monkeypatch):
    app.config.update({'GOOGLE_CLIENT_ID': 'client', 'GOOGLE_CLIENT_SECRET': 'secret'})

    def fake_post(url, data=None, timeout=None, headers=None):
        assert 'oauth2.googleapis.com/token' in url
        assert data['code'] == 'test-code'
        return DummyResponse({'access_token': 'token-123'})

    def fake_get(url, headers=None, params=None, timeout=None):
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer token-123'
        return DummyResponse({'sub': 'abc123', 'email': 'user@example.com', 'name': 'Example User'})

    monkeypatch.setattr('integrations.sso.requests.post', fake_post)
    monkeypatch.setattr('integrations.sso.requests.get', fake_get)

    response = client.get('/login/google/start?next=/profile')
    assert response.status_code == 302
    assert 'accounts.google.com' in response.location
    query = parse_qs(urlparse(response.location).query)
    assert query['client_id'] == ['client']

    with client.session_transaction() as session:
        state = session['oauth_state']['value']

    response = client.get(f'/oauth/google/callback?state={state}&code=test-code')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/profile')

    with client.session_transaction() as session:
        assert session.get('_user_id') is not None
        assert 'oauth_state' not in session

    with app.app_context():
        user = User.query.filter_by(email='user@example.com').first()
        assert user is not None
        assert user.auth_provider == 'google'
        assert user.auth_provider_id == 'abc123'
        assert user.password_hash is None


def test_facebook_oauth_requires_email(client, app, monkeypatch):
    app.config.update({'FACEBOOK_CLIENT_ID': 'fb', 'FACEBOOK_CLIENT_SECRET': 'secret'})

    def fake_get(url, params=None, timeout=None):
        if 'oauth/access_token' in url:
            return DummyResponse({'access_token': 'token-123'})
        if url.endswith('/me'):
            return DummyResponse({'id': 'fb123', 'name': 'No Email User'})
        raise AssertionError('unexpected url')

    monkeypatch.setattr('integrations.sso.requests.get', fake_get)

    response = client.get('/login/facebook/start')
    assert response.status_code == 302

    with client.session_transaction() as session:
        state = session['oauth_state']['value']

    response = client.get(f'/oauth/facebook/callback?state={state}&code=abc')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')

    with client.session_transaction() as session:
        assert session.get('_user_id') is None

    with app.app_context():
        assert User.query.count() == 0


def test_apple_oauth_creates_user(client, app, monkeypatch):
    app.config.update({'APPLE_CLIENT_ID': 'apple-client', 'APPLE_CLIENT_SECRET': 'apple-secret'})

    token = _build_id_token({'sub': 'apple123', 'email': 'apple@example.com'})

    def fake_post(url, data=None, headers=None, timeout=None):
        assert 'appleid.apple.com/auth/token' in url
        return DummyResponse({'id_token': token})

    def fail_get(*args, **kwargs):  # pragma: no cover - defensive
        raise AssertionError('GET should not be called for Apple provider')

    monkeypatch.setattr('integrations.sso.requests.post', fake_post)
    monkeypatch.setattr('integrations.sso.requests.get', fail_get)

    response = client.get('/login/apple/start')
    assert response.status_code == 302

    with client.session_transaction() as session:
        state = session['oauth_state']['value']

    response = client.get(f'/oauth/apple/callback?state={state}&code=abc')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/')

    with client.session_transaction() as session:
        assert session.get('_user_id') is not None

    with app.app_context():
        user = User.query.filter_by(email='apple@example.com').first()
        assert user is not None
        assert user.auth_provider == 'apple'
        assert user.auth_provider_id == 'apple123'
        assert user.password_hash is None

        # Ensure additional sign-ins reuse the same account
        db.session.remove()
        second = User.query.filter_by(email='apple@example.com').first()
        assert second.id == user.id
