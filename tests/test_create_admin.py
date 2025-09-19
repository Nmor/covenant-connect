"""Tests for the administrative account creation helper."""

import pytest

from create_admin import create_admin_user
from models import User


def test_create_admin_is_idempotent(app):
    """Running the helper twice should not create duplicate accounts."""

    password = "Str0ngPass!word"

    with app.app_context():
        assert create_admin_user("admin", "admin@example.com", password) is True
        assert User.query.filter_by(email="admin@example.com").count() == 1

        assert create_admin_user("admin", "admin@example.com", password) is False
        assert User.query.filter_by(email="admin@example.com").count() == 1


def test_create_admin_rejects_weak_password(app):
    """Weak credentials must be rejected to meet the password policy."""

    with app.app_context():
        with pytest.raises(ValueError):
            create_admin_user("admin", "admin@example.com", "weakpass")
