from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    notification_preferences = db.Column(db.JSON, default=dict)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PrayerRequest(db.Model):
    __tablename__ = 'prayer_requests'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    request = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))

    facility_reservations = db.relationship(
        'FacilityReservation',
        back_populates='event',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    attendance_records = db.relationship(
        'AttendanceRecord',
        back_populates='event',
        cascade='all, delete-orphan',
        order_by='AttendanceRecord.check_in_time.desc()'
    )

    @property
    def total_checked_in(self):
        return sum(record.checked_in_count or 0 for record in self.attendance_records)

    @property
    def peak_attendance(self):
        counts = [record.checked_in_count or 0 for record in self.attendance_records]
        return max(counts) if counts else 0

class Sermon(db.Model):
    __tablename__ = 'sermons'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    preacher = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    media_url = db.Column(db.String(500))
    media_type = db.Column(db.String(20))

class Gallery(db.Model):
    __tablename__ = 'gallery'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    image_url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Church(db.Model):
    __tablename__ = 'churches'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Donation(db.Model):
    __tablename__ = 'donations'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    reference = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True)
    error_message = db.Column(db.Text)
    payment_info = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(200), nullable=False, default='Covenant Connect')
    logo_url = db.Column(db.String(500))
    theme_preference = db.Column(db.String(20), default='dark')
    addresses = db.Column(db.JSON, default=list)
    social_media_links = db.Column(db.JSON, default=dict)
    contact_info = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Facility(db.Model):
    __tablename__ = 'facilities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(200))
    capacity = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    reservations = db.relationship(
        'FacilityReservation',
        back_populates='facility',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    resources = db.relationship(
        'Resource',
        back_populates='facility',
        cascade='all, delete-orphan'
    )


class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100))
    quantity_available = db.Column(db.Integer, nullable=False, default=1)
    description = db.Column(db.Text)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    facility = db.relationship('Facility', back_populates='resources')

    allocations = db.relationship(
        'ResourceAllocation',
        back_populates='resource',
        cascade='all, delete-orphan'
    )


class FacilityReservation(db.Model):
    __tablename__ = 'facility_reservations'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), nullable=False)
    ministry_name = db.Column(db.String(150), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(40), nullable=False, default='requested')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = db.relationship('Event', back_populates='facility_reservations')
    facility = db.relationship('Facility', back_populates='reservations')

    resource_requests = db.relationship(
        'ResourceAllocation',
        back_populates='reservation',
        cascade='all, delete-orphan'
    )


class ResourceAllocation(db.Model):
    __tablename__ = 'resource_allocations'
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('facility_reservations.id'), nullable=False)
    resource_id = db.Column(db.Integer, db.ForeignKey('resources.id'), nullable=False)
    quantity_requested = db.Column(db.Integer, nullable=False, default=1)
    quantity_approved = db.Column(db.Integer)
    notes = db.Column(db.Text)

    reservation = db.relationship('FacilityReservation', back_populates='resource_requests')
    resource = db.relationship('Resource', back_populates='allocations')


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    expected_attendees = db.Column(db.Integer)
    checked_in_count = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text)

    event = db.relationship('Event', back_populates='attendance_records')
