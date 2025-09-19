"""Application factory and extension setup for Covenant Connect."""
from __future__ import annotations

import logging
import logging
from datetime import datetime
from typing import Any

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

try:  # pragma: no cover - optional dependency for background tasks
    from redis import Redis
    from rq import Queue
except Exception:  # pragma: no cover - executed when redis/rq unavailable
    Redis = None  # type: ignore
    Queue = None  # type: ignore

from config import Config


db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
cors = CORS()


def _configure_logging(app: Flask) -> None:
    """Configure a simple application-wide logger."""

    app.logger.setLevel(logging.INFO)

    if not app.logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)

    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def _initialize_queue(app: Flask) -> None:
    """Attach an RQ queue to the app when Redis is available."""

    app.task_queue = None  # type: ignore[attr-defined]
    app.redis_connection = None  # type: ignore[attr-defined]

    if not Redis or not Queue:
        app.logger.info('Redis/RQ not available; background jobs disabled.')
        return

    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    try:
        connection = Redis.from_url(redis_url)
        queue = Queue(connection=connection)
    except Exception as exc:  # pragma: no cover - defensive log
        app.logger.warning('Unable to connect to Redis at %s: %s', redis_url, exc)
        return

    app.redis_connection = connection  # type: ignore[attr-defined]
    app.task_queue = queue  # type: ignore[attr-defined]


def _warn_insecure_config(app: Flask) -> None:
    """Emit warnings when security-related config deviates in production."""

    if not app.config.get('IS_PRODUCTION'):
        return

    insecure_flags: list[str] = []

    if not app.config.get('SESSION_COOKIE_SECURE', False):
        insecure_flags.append('SESSION_COOKIE_SECURE')
    if not app.config.get('REMEMBER_COOKIE_SECURE', False):
        insecure_flags.append('REMEMBER_COOKIE_SECURE')
    if not app.config.get('SESSION_COOKIE_HTTPONLY', False):
        insecure_flags.append('SESSION_COOKIE_HTTPONLY')

    samesite = app.config.get('SESSION_COOKIE_SAMESITE')
    if isinstance(samesite, str) and samesite.lower() not in {'lax', 'strict'}:
        insecure_flags.append('SESSION_COOKIE_SAMESITE')

    if app.config.get('PREFERRED_URL_SCHEME', 'http') != 'https':
        insecure_flags.append('PREFERRED_URL_SCHEME')

    if insecure_flags:
        app.logger.warning(
            'Production security defaults overridden: %s',
            ', '.join(sorted(insecure_flags)),
        )

    cors_origins = app.config.get('CORS_ORIGINS')
    if cors_origins in ('*', ['*']):
        app.logger.warning(
            'CORS_ORIGINS allows any origin while running in production. '
            'Set CORS_ORIGINS to an explicit list of domains.',
        )


def create_app(config_object: type[Config] | None = None) -> Flask:
    """Create and configure a :class:`~flask.Flask` application."""

    app = Flask(__name__)
    app.config.from_object(config_object or Config)

    _configure_logging(app)

    # Configure secret key explicitly to aid tests
    secret_key = app.config.get('SECRET_KEY') or 'dev-secret-key'
    app.config['SECRET_KEY'] = secret_key

    _warn_insecure_config(app)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config.get('CORS_ORIGINS', '*')}})

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    _initialize_queue(app)

    from routes.home import home_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.admin_reports import admin_reports_bp
    from routes.prayers import prayers_bp
    from routes.events import events_bp
    from routes.sermons import sermons_bp
    from routes.gallery import gallery_bp
    from routes.donations import donations_bp
    from routes.notifications import notifications_bp
    from routes.solutions import solutions_bp
    from routes.internal import internal_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_reports_bp)
    app.register_blueprint(prayers_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(sermons_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(solutions_bp)
    app.register_blueprint(internal_bp)

    @app.context_processor
    def inject_year() -> dict[str, Any]:
        return {'current_year': datetime.utcnow().year}

    from models import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        if not user_id:
            return None
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    return app


__all__ = ['create_app', 'db', 'login_manager', 'mail', 'csrf', 'cors']
