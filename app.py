from flask import Flask, render_template, request, g, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf import CSRFProtect
codex/explain-requested-code-functionality-dxdu2u
from flask_cors import CORS
from redis import Redis
from rq import Queue
from redis import Redis
from rq import Queue
import os
main
from datetime import datetime
import logging
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()
codex/explain-requested-code-functionality-dxdu2u
cors = CORS()
redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
task_queue = Queue(connection=redis_conn)
main

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('covenant_connect')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
codex/explain-requested-code-functionality-dxdu2u

    if Config.SECRET_KEY == 'dev-secret-key':
        logger.warning('SECRET_KEY is not set. Using development key.')
    
    # Configure database
    database_url = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    if not database_url:
        raise RuntimeError('DATABASE_URL is not set')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configure secret key
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        secret_key = 'dev-secret-key'
        logger.warning('SECRET_KEY is not set. Using development key.')
    app.config['SECRET_KEY'] = secret_key

    # Email configuration
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
main

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
codex/explain-requested-code-functionality-dxdu2u
    cors.init_app(app, resources={r"/*": {"origins": app.config['CORS_ORIGINS']}})
 main
    login_manager.login_view = 'auth.login'
    app.task_queue = task_queue

    # Initialize task queue lazily
    redis_conn = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = Queue(connection=redis_conn)

    # Register blueprints
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
 codex/find-current-location-in-codebase-aqxt07
    from routes.solutions import solutions_bp
 codex/find-current-location-in-codebase-ntia0s
    from routes.solutions import solutions_bp
    from routes.internal import internal_bp
     main
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
 codex/find-current-location-in-codebase-aqxt07
    app.register_blueprint(solutions_bp)
 codex/find-current-location-in-codebase-ntia0s
    app.register_blueprint(solutions_bp)
    app.register_blueprint(internal_bp)
     main
    # Context processors
    @app.context_processor
    def inject_year():
        return {'current_year': datetime.utcnow().year}

    # Load user
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app
