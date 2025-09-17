from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notification_preferences = db.Column(db.JSON, default=dict)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Church(db.Model):
    __tablename__ = 'churches'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Donation(db.Model):
    __tablename__ = 'donations'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    payment_method = db.Column(db.String(40), nullable=False)
    reference = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='received')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'email': self.email,
            'amount': Decimal(self.amount),
            'currency': self.currency,
            'payment_method': self.payment_method,
            'reference': self.reference,
            'status': self.status,
            'created_at': self.created_at,
        }


class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    recurrence_rule = db.Column(db.String(255))
    recurrence_end_date = db.Column(db.DateTime)
    service_segments = db.Column(db.JSON, default=list)
    ministry_tags = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_service_segments(self, segments: list[dict[str, str]]) -> None:
        cleaned: list[dict[str, str]] = []
        for segment in segments:
            if not any(segment.values()):
                continue
            cleaned.append({
                'title': segment.get('title', '').strip(),
                'leader': segment.get('leader', '').strip(),
                'duration': segment.get('duration', '').strip(),
                'notes': segment.get('notes', '').strip(),
            })
        self.service_segments = cleaned

    def set_ministry_tags(self, tags: list[str]) -> None:
        cleaned = [tag.strip() for tag in tags if tag.strip()]
        self.ministry_tags = cleaned


class Sermon(db.Model):
    __tablename__ = 'sermons'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    preacher = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    media_url = db.Column(db.String(500))
    media_type = db.Column(db.String(20))


class PrayerRequest(db.Model):
    __tablename__ = 'prayer_requests'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    request = db.Column(db.Text, nullable=False)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Gallery(db.Model):
    __tablename__ = 'gallery'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    image_url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
