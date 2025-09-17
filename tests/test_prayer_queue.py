import re

from tasks import send_prayer_notification


def get_token(client, path):
    resp = client.get(path)
    return re.search("name='csrf_token' value='([^']+)'", resp.data.decode()).group(1)


def test_prayer_enqueue(monkeypatch, client, app):
    calls = {}

    class DummyQueue:
        def enqueue(self, func, arg):
            calls['func'] = func
            calls['arg'] = arg

    with app.app_context():
        app.task_queue = DummyQueue()

    token = get_token(client, '/prayers')
    client.post('/prayers/submit', data={
        'csrf_token': token,
        'name': 'John',
        'email': 'john@example.com',
        'request': 'prayer'
    }, follow_redirects=True)

    assert calls['func'] == send_prayer_notification
    assert isinstance(calls['arg'], int)
