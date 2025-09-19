import pytest

from app import db
from integrations import EmailIntegrationManager
from models import ServiceIntegration


@pytest.fixture(autouse=True)
def configure_sender(app):
    with app.app_context():
        app.config['MAIL_DEFAULT_SENDER'] = 'noreply@example.com'
        yield


def test_mailgun_integration_sends_via_api(app, monkeypatch):
    with app.app_context():
        integration = ServiceIntegration(
            service='email',
            provider='mailgun',
            display_name='Mailgun',
            config={
                'api_key': 'key-test',
                'domain': 'mg.example.com',
                'sender_email': 'alerts@example.com',
            },
            is_active=True,
        )
        db.session.add(integration)
        db.session.commit()

        captured = {}

        class DummyResponse:
            status_code = 200
            text = 'ok'

        def fake_post(url, auth=None, data=None, timeout=None):
            captured['url'] = url
            captured['auth'] = auth
            captured['data'] = data
            captured['timeout'] = timeout
            return DummyResponse()

        fallback_calls = []

        monkeypatch.setattr('integrations.email.requests.post', fake_post)
        monkeypatch.setattr('integrations.email.mail.send', lambda message: fallback_calls.append(message))

        EmailIntegrationManager.send_email('Subject', 'Body', ['user@example.com'])

        assert captured['url'] == 'https://api.mailgun.net/v3/mg.example.com/messages'
        assert captured['auth'] == ('api', 'key-test')
        assert captured['data']['subject'] == 'Subject'
        assert captured['data']['to'] == ['user@example.com']
        assert fallback_calls == []


def test_fallback_to_flask_mail_when_no_integration(app, monkeypatch):
    with app.app_context():
        sent_messages = []

        def fake_send(message):
            sent_messages.append(message)

        monkeypatch.setattr('integrations.email.mail.send', fake_send)

        EmailIntegrationManager.send_email('Fallback', 'Body', ['user@example.com'])

        assert len(sent_messages) == 1
        assert sent_messages[0].subject == 'Fallback'
        assert sent_messages[0].recipients == ['user@example.com']


def test_aws_ses_integration_uses_boto3_client(app, monkeypatch):
    with app.app_context():
        integration = ServiceIntegration(
            service='email',
            provider='aws_ses',
            display_name='Amazon SES',
            config={
                'access_key_id': 'AKIA',
                'secret_access_key': 'SECRET',
                'region': 'us-east-1',
                'sender_email': 'verified@example.com',
            },
            is_active=True,
        )
        db.session.add(integration)
        db.session.commit()

        captured = {}

        class DummyClient:
            def send_email(self, **kwargs):
                captured.update(kwargs)
                return {'MessageId': '123'}

        monkeypatch.setattr('integrations.email.boto3.client', lambda *args, **kwargs: DummyClient())
        monkeypatch.setattr('integrations.email.mail.send', lambda message: (_ for _ in ()).throw(RuntimeError('should not fallback')))

        EmailIntegrationManager.send_email('SES subject', 'SES body', ['user@example.com'])

        assert captured['Source'] == 'verified@example.com'
        assert captured['Destination']['ToAddresses'] == ['user@example.com']
        assert captured['Message']['Subject']['Data'] == 'SES subject'
