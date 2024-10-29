from flask import Flask, render_template, request, g, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mail import Mail
import os
from datetime import datetime
import logging

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('covenant_connect')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.urandom(24)

    # Email configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from routes.home import home_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.prayers import prayers_bp
    from routes.events import events_bp
    from routes.sermons import sermons_bp
    from routes.gallery import gallery_bp
    from routes.donations import donations_bp
    from routes.notifications import notifications_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(prayers_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(sermons_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(notifications_bp)

    # Context processors
    @app.context_processor
    def inject_year():
        return {'current_year': datetime.utcnow().year}

    # Load user
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
