import re
from models import User, Church
from app import db


def get_token(client, path):
    resp = client.get(path)
    token = re.search("name='csrf_token' value='([^']+)'", resp.data.decode()).group(1)
    return token


def login(client, app):
    with app.app_context():
        user = User(username='manager', email='manager@example.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    token = get_token(client, '/login')
    client.post('/login', data={
        'csrf_token': token,
        'email': 'manager@example.com',
        'password': 'password'
    }, follow_redirects=True)


def test_church_list_requires_login(client):
    resp = client.get('/churches')
    assert resp.status_code == 302


def test_add_church(client, app):
    login(client, app)
    token = get_token(client, '/churches/add')
    client.post('/churches/add', data={
        'csrf_token': token,
        'name': 'Central Church',
        'address': '123 Main St'
    }, follow_redirects=True)
    with app.app_context():
        church = Church.query.filter_by(name='Central Church').first()
        assert church is not None
        assert church.address == '123 Main St'
