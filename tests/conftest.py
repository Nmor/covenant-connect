import os
import sys
from pathlib import Path

import pytest
from flask_migrate import Migrate, downgrade, upgrade

sys.path.append(os.path.abspath(os.curdir))
from app import create_app, db


@pytest.fixture
def app(tmp_path: Path):
    app = create_app()
    app.config.update(
        {
            'TESTING': True,
            'PAYSTACK_SECRET_KEY': 'test-paystack',
            'FINCRA_SECRET_KEY': 'test-fincra',
            'STRIPE_SECRET_KEY': 'test-stripe',
            'FLUTTERWAVE_SECRET_KEY': 'test-flutterwave',
        }
    )
    database_path = tmp_path / "test.db"
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{database_path}"
    Migrate(app, db)
    with app.app_context():
        upgrade()
        yield app
        db.session.remove()
        downgrade(revision='base')
    database_path.unlink(missing_ok=True)


@pytest.fixture
def client(app):
    return app.test_client()
