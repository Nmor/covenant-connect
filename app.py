import logging
import os
from datetime import datetime

from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from redis import Redis
from rq import Queue

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
cors = CORS()
task_queue: Queue | None = None


def _configure_logging() -> logging.Logger:
    logger = logging.getLogger('covenant_connect')
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(handler)

    return logger


def _configure_secrets(app: Flask, logger: logging.Logger) -> None:
    secret_key = os.getenv('SECRET_KEY') or 'dev-secret-key'
    if secret_key == 'dev-secret-key':
        logger.warning('SECRET_KEY is not set. Using development key.')
    app.config['SECRET_KEY'] = secret_key


def _configure_database(app: Flask) -> None:
    database_url = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    if not database_url:
        raise RuntimeError('DATABASE_URL is not set')

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


def _configure_mail(app: Flask) -> None:
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')


def _configure_integrations(app: Flask) -> Queue:
    app.config.setdefault('REDIS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    app.config.setdefault('CORS_ORIGINS', ['*'])

    redis_connection = Redis.from_url(app.config['REDIS_URL'])
    queue = Queue(connection=redis_connection)

    cors.init_app(app, resources={r'/*': {'origins': app.config['CORS_ORIGINS']}})

    return queue


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    logger = _configure_logging()
    _configure_secrets(app, logger)
    _configure_database(app)
    _configure_mail(app)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'

    queue = _configure_integrations(app)
    global task_queue
    task_queue = queue
    app.task_queue = queue

    from routes.admin import admin_bp
    from routes.admin_reports import admin_reports_bp
    from routes.auth import auth_bp
    from routes.donations import donations_bp
    from routes.events import events_bp
    from routes.gallery import gallery_bp
    from routes.home import home_bp
    from routes.internal import internal_bp
    from routes.notifications import notifications_bp
    from routes.prayers import prayers_bp
    from routes.sermons import sermons_bp
    from routes.solutions import solutions_bp

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
    def inject_year() -> dict[str, int]:
        return {'current_year': datetime.utcnow().year}

    from models import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    return app
