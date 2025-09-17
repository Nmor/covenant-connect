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
    member_profile = db.relationship('Member', back_populates='user', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
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

    def __repr__(self) -> str:  # pragma: no cover - representation helper
        return f"<Household {self.name!r}>"


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
        order_by='CareInteraction.interaction_date DESC',
        cascade='all, delete-orphan',
    )

    def __repr__(self) -> str:  # pragma: no cover - representation helper
        return f"<Member {self.full_name}>"

    @property
    def full_name(self) -> str:
        return " ".join(filter(None, [self.first_name, self.last_name])).strip()

    @property
    def milestone_counts(self) -> tuple[int, int]:
        data = self.milestones or {}
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
    metadata = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    member = db.relationship('Member', back_populates='care_interactions')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self) -> str:  # pragma: no cover - representation helper
        return f"<CareInteraction {self.interaction_type} for member {self.member_id}>"

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
 codex/expand-event-model-for-recurrence-and-tags
    recurrence_rule = db.Column(db.String(255))
    recurrence_end_date = db.Column(db.DateTime)
    service_segments = db.Column(db.JSON, default=list)
    ministry_tags = db.Column(db.JSON, default=list)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('ministry_departments.id', ondelete='SET NULL'),
        nullable=True
    )
    volunteer_role_id = db.Column(
        db.Integer,
        db.ForeignKey('volunteer_roles.id', ondelete='SET NULL'),
        nullable=True
    )

    department = db.relationship('MinistryDepartment', back_populates='events')
    volunteer_role = db.relationship('VolunteerRole', back_populates='events')
   main

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


class MinistryDepartment(db.Model):
    __tablename__ = 'ministry_departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text)
    lead_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = db.relationship(
        'User',
        backref=db.backref('led_departments', lazy='dynamic'),
        foreign_keys=[lead_id]
    )
    roles = db.relationship(
        'VolunteerRole',
        back_populates='department',
        cascade='all, delete-orphan',
        order_by='VolunteerRole.name'
    )
    events = db.relationship('Event', back_populates='department')


class VolunteerRole(db.Model):
    __tablename__ = 'volunteer_roles'
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('ministry_departments.id', ondelete='CASCADE'),
        nullable=False
    )
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    coordinator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = db.relationship('MinistryDepartment', back_populates='roles')
    coordinator = db.relationship(
        'User',
        backref=db.backref('coordinated_roles', lazy='dynamic'),
        foreign_keys=[coordinator_id]
    )
    assignments = db.relationship(
        'VolunteerAssignment',
        back_populates='role',
        cascade='all, delete-orphan'
    )
    events = db.relationship('Event', back_populates='volunteer_role')


class VolunteerAssignment(db.Model):
    __tablename__ = 'volunteer_assignments'
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(
        db.Integer,
        db.ForeignKey('volunteer_roles.id', ondelete='CASCADE'),
        nullable=False
    )
    volunteer_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role = db.relationship('VolunteerRole', back_populates='assignments')
    volunteer = db.relationship(
        'User',
        backref=db.backref('volunteer_assignments', cascade='all, delete-orphan')
    )

    __table_args__ = (
        db.UniqueConstraint('role_id', 'volunteer_id', name='uq_role_volunteer'),
    )
