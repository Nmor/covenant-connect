import os
import sys

import pytest

sys.path.append(os.path.abspath(os.curdir))
from app import create_app, db


@pytest.fixture
def app():
    app = create_app()
    app.config.update({'TESTING': True})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
