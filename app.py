import logging
import os
from datetime import datetime

 codex/add-generic-workflow-runner-and-ui
from flask import Flask, render_template, request, g, session, redirect, url_for
from flask import Flask
     main
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
 codex/add-generic-workflow-runner-and-ui

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
task_queue = Queue(connection=redis_conn)
 codex/expand-event-model-for-recurrence-and-tags
  
redis_conn = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
task_queue = Queue(connection=redis_conn)
     main

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('covenant_connect')
 codex/add-generic-workflow-runner-and-ui
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    if not any(isinstance(existing, logging.StreamHandler) for existing in logger.handlers):
 codex/expand-event-model-for-recurrence-and-tags
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
     main
        logger.addHandler(handler)

    if Config.SECRET_KEY == 'dev-secret-key':
        logger.warning('SECRET_KEY is not set. Using development key.')
 codex/add-generic-workflow-runner-and-ui

    # Configure database
     main
    database_url = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    if not database_url:
        raise RuntimeError('DATABASE_URL is not set')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

 codex/expand-event-model-for-recurrence-and-tags
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        secret_key = 'dev-secret-key'
        logger.warning('SECRET_KEY is not set. Using development key.')
    app.config['SECRET_KEY'] = secret_key

    app.config.setdefault('REDIS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    app.config.setdefault('CORS_ORIGINS', ['*'])
    secret_key = os.getenv('SECRET_KEY') or 'dev-secret-key'
    if secret_key == 'dev-secret-key':
        logger.warning('SECRET_KEY is not set. Using development key.')
    app.config['SECRET_KEY'] = secret_key

     main
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
 codex/add-generic-workflow-runner-and-ui

    if not app.config.get('CORS_ORIGINS'):
        app.config['CORS_ORIGINS'] = ['*']
     main

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
 codex/add-generic-workflow-runner-and-ui
    cors.init_app(app, resources={r"/*": {"origins": app.config['CORS_ORIGINS']}})
    login_manager.login_view = 'auth.login'

    # Initialize task queue
    redis_url = app.config.get('REDIS_URL') or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    redis_connection = Redis.from_url(redis_url)
    app.task_queue = Queue(connection=redis_connection)
 codex/expand-event-model-for-recurrence-and-tags
    cors.init_app(app, resources={r'/*': {'origins': app.config['CORS_ORIGINS']}})

    login_manager.login_view = 'auth.login'

    redis_connection = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = Queue(connection=redis_connection)
    cors.init_app(app, resources={r"/*": {"origins": app.config.get('CORS_ORIGINS', '*')}})

    login_manager.login_view = 'auth.login'

    redis_url = app.config.get('REDIS_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    redis_connection = Redis.from_url(redis_url)
    app.task_queue = Queue(connection=redis_connection)

    global task_queue
    task_queue = app.task_queue
     main

    from routes.home import home_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
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
    app.register_blueprint(prayers_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(sermons_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(solutions_bp)
    app.register_blueprint(internal_bp)

    @app.context_processor
    def inject_year():
        return {'current_year': datetime.utcnow().year}

    from models import User

    @login_manager.user_loader
 codex/add-generic-workflow-runner-and-ui
    def load_user(user_id: str):
    def load_user(user_id: str) -> User | None:
     main
        return db.session.get(User, int(user_id))

    return app
