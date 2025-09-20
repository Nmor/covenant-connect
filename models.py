"""Database models used by the Covenant Connect application."""
from __future__ import annotations

from datetime import datetime, date
from typing import Any

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.UniqueConstraint(
            'auth_provider', 'auth_provider_id', name='uq_users_provider_identity'
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    notification_preferences = db.Column(db.JSON, default=dict)
    auth_provider = db.Column(db.String(50))
    auth_provider_id = db.Column(db.String(255))

    member_profile = db.relationship('Member', back_populates='user', uselist=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Household(db.Model):
    __tablename__ = 'households'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    primary_email = db.Column(db.String(120))
    primary_phone = db.Column(db.String(50))
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship(
        'Member',
        back_populates='household',
        cascade='all, delete-orphan',
        order_by='Member.last_name',
    )


class Member(db.Model):
    __tablename__ = 'members'

    DEFAULT_MILESTONES = [
        ('first_visit', 'First Visit'),
        ('next_steps', 'Next Steps Class'),
        ('serve_team', 'Serving Team'),
        ('community_group', 'Joined a Community Group'),
        ('prayer_connection', 'Shared a Prayer Request'),
        ('sermon_engagement', 'Engaged with a Sermon'),
    ]

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(20))
    marital_status = db.Column(db.String(50))
    membership_status = db.Column(db.String(50), default='guest')
    assimilation_stage = db.Column(db.String(100))
    campus = db.Column(db.String(120))
    milestones = db.Column(db.JSON, default=dict)
    notes = db.Column(db.Text)
    preferred_contact_method = db.Column(db.String(50))
    joined_at = db.Column(db.Date)
    last_interaction_at = db.Column(db.DateTime)
    next_follow_up_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'))

    user = db.relationship('User', back_populates='member_profile')
    household = db.relationship('Household', back_populates='members')
    care_interactions = db.relationship(
        'CareInteraction',
        back_populates='member',
        order_by='CareInteraction.interaction_date.desc()',
        cascade='all, delete-orphan',
    )

    def __repr__(self) -> str:  # pragma: no cover - repr helper
        return f"<Member {self.full_name}>"

    @property
    def full_name(self) -> str:
        return " ".join(filter(None, [self.first_name, self.last_name])).strip()

    @property
    def milestone_counts(self) -> tuple[int, int]:
        data: dict[str, Any] = self.milestones or {}
        default_keys = [key for key, _ in self.DEFAULT_MILESTONES]

        total = len(default_keys)
        completed = 0

        for key in default_keys:
            if data.get(key, {}).get('completed'):
                completed += 1

        extra_keys = [key for key in data.keys() if key not in default_keys]
        total += len(extra_keys)
        for key in extra_keys:
            if data.get(key, {}).get('completed'):
                completed += 1

        return completed, total

    @property
    def milestone_completion_rate(self) -> float:
        completed, total = self.milestone_counts
        if total == 0:
            return 0.0
        return completed / total

    @property
    def milestone_completion_percent(self) -> int:
        return int(round(self.milestone_completion_rate * 100))

    @property
    def follow_up_due(self) -> bool:
        if not self.next_follow_up_date:
            return False
        return self.next_follow_up_date.date() <= datetime.utcnow().date()

    def record_milestone(
        self,
        key: str,
        label: str | None = None,
        *,
        completed: bool = True,
        completed_on: datetime | None = None,
    ) -> None:
        data = dict(self.milestones or {})
        data[key] = {
            'label': label or self.milestone_label(key),
            'completed': completed,
            'completed_on': (
                (completed_on or datetime.utcnow()).isoformat()
                if completed
                else None
            ),
        }
        self.milestones = data

    @classmethod
    def milestone_label(cls, key: str) -> str:
        for default_key, default_label in cls.DEFAULT_MILESTONES:
            if default_key == key:
                return default_label
        return key.replace('_', ' ').title()


class CareInteraction(db.Model):
    __tablename__ = 'care_interactions'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    interaction_type = db.Column(db.String(50), nullable=False)
    interaction_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    notes = db.Column(db.Text)
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.DateTime)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    source = db.Column(db.String(100))
    extra_data = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    member = db.relationship('Member', back_populates='care_interactions')
    created_by = db.relationship('User', foreign_keys=[created_by_id])


class PrayerRequest(db.Model):
    __tablename__ = 'prayer_requests'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    request = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)


class MinistryDepartment(db.Model):
    __tablename__ = 'ministry_departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    lead_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = db.relationship('User', backref=db.backref('led_departments', lazy='dynamic'))
    roles = db.relationship(
        'VolunteerRole',
        back_populates='department',
        cascade='all, delete-orphan',
        order_by='VolunteerRole.name',
    )
    events = db.relationship('Event', back_populates='department')


class VolunteerRole(db.Model):
    __tablename__ = 'volunteer_roles'

    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('ministry_departments.id', ondelete='CASCADE'),
        nullable=False,
    )
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    coordinator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    needed_volunteers = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = db.relationship('MinistryDepartment', back_populates='roles')
    coordinator = db.relationship(
        'User',
        backref=db.backref('coordinated_roles', lazy='dynamic'),
        foreign_keys=[coordinator_id],
    )
    assignments = db.relationship(
        'VolunteerAssignment',
        back_populates='role',
        cascade='all, delete-orphan',
    )
    events = db.relationship('Event', back_populates='volunteer_role')


class VolunteerAssignment(db.Model):
    __tablename__ = 'volunteer_assignments'

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(
        db.Integer,
        db.ForeignKey('volunteer_roles.id', ondelete='CASCADE'),
        nullable=False,
    )
    volunteer_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role = db.relationship('VolunteerRole', back_populates='assignments')
    volunteer = db.relationship('User', backref=db.backref('volunteer_assignments', cascade='all, delete-orphan'))
    event = db.relationship('Event', back_populates='volunteer_assignments')


class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    campus = db.Column(db.String(120))
    recurrence_rule = db.Column(db.String(255))
    recurrence_end_date = db.Column(db.DateTime)
    service_segments = db.Column(db.JSON, default=list)
    ministry_tags = db.Column(db.JSON, default=list)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('ministry_departments.id', ondelete='SET NULL'),
    )
    volunteer_role_id = db.Column(
        db.Integer,
        db.ForeignKey('volunteer_roles.id', ondelete='SET NULL'),
    )

    department = db.relationship('MinistryDepartment', back_populates='events')
    volunteer_role = db.relationship('VolunteerRole', back_populates='events')
    facility_reservations = db.relationship(
        'FacilityReservation',
        back_populates='event',
        cascade='all, delete-orphan',
    )
    attendance_records = db.relationship(
        'AttendanceRecord',
        back_populates='event',
        cascade='all, delete-orphan',
        order_by='AttendanceRecord.check_in_time.desc()',
    )
    volunteer_assignments = db.relationship(
        'VolunteerAssignment',
        back_populates='event',
        cascade='all, delete-orphan',
    )

    @property
    def total_checked_in(self) -> int:
        return sum(record.checked_in_count or 0 for record in self.attendance_records)

    @property
    def peak_attendance(self) -> int:
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


class ServiceIntegration(db.Model):
    __tablename__ = 'service_integrations'

    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(50), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    config = db.Column(db.JSON, default=dict)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('service', 'provider', name='uq_service_provider'),
    )


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


class Automation(db.Model):
    __tablename__ = 'automations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    trigger = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    default_channel = db.Column(db.String(50))
    target_department = db.Column(db.String(120))
    trigger_filters = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = db.relationship(
        'AutomationStep',
        back_populates='automation',
        cascade='all, delete-orphan',
        order_by='AutomationStep.order',
    )


class AutomationStep(db.Model):
    __tablename__ = 'automation_steps'

    id = db.Column(db.Integer, primary_key=True)
    automation_id = db.Column(db.Integer, db.ForeignKey('automations.id'), nullable=False)
    title = db.Column(db.String(150))
    action_type = db.Column(db.String(50), nullable=False)
    channel = db.Column(db.String(50))
    department = db.Column(db.String(120))
    order = db.Column(db.Integer, default=0)
    delay_minutes = db.Column(db.Integer, default=0)
    config = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    automation = db.relationship('Automation', back_populates='steps')


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
    )
    resources = db.relationship(
        'Resource',
        back_populates='facility',
        cascade='all, delete-orphan',
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
        cascade='all, delete-orphan',
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

    event = db.relationship('Event', back_populates='facility_reservations')
    facility = db.relationship('Facility', back_populates='reservations')
    resource_requests = db.relationship(
        'ResourceAllocation',
        back_populates='reservation',
        cascade='all, delete-orphan',
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
    role_id = db.Column(db.Integer, db.ForeignKey('volunteer_roles.id'))
    volunteer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    expected_attendees = db.Column(db.Integer)
    checked_in_count = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text)

    event = db.relationship('Event', back_populates='attendance_records')
    role = db.relationship('VolunteerRole', backref=db.backref('attendance_records', lazy='dynamic'))
    volunteer = db.relationship('User', backref=db.backref('attendance_records', lazy='dynamic'))


__all__ = [
    'AttendanceRecord',
    'Automation',
    'AutomationStep',
    'CareInteraction',
    'Church',
    'Donation',
    'Event',
    'Facility',
    'FacilityReservation',
    'Gallery',
    'Household',
    'Member',
    'MinistryDepartment',
    'PrayerRequest',
    'Resource',
    'ResourceAllocation',
    'ServiceIntegration',
    'Sermon',
    'Settings',
    'User',
    'VolunteerAssignment',
    'VolunteerRole',
]
