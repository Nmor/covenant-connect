from flask import Flask, render_template, request, g, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_babel import Babel
import os
from datetime import datetime
import logging

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
babel = Babel()

def get_locale():
    # First try to get locale from query parameter
    locale = request.args.get('lang')
    app.logger.debug(f"Requested locale: {locale}")
    
    if locale in ['en', 'es', 'fr']:
        app.logger.debug(f"Valid locale found in query parameters: {locale}")
        session['lang'] = locale
        return locale
    
    # Then try to get locale from session
    if 'lang' in session and session['lang'] in ['en', 'es', 'fr']:
        app.logger.debug(f"Using locale from session: {session['lang']}")
        return session['lang']
    
    # Finally, use browser's preferred language    
    best_match = request.accept_languages.best_match(['en', 'es', 'fr'])
    app.logger.debug(f"Using browser's preferred language: {best_match}")
    return best_match

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
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

    # Babel configuration
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    babel.init_app(app, locale_selector=get_locale)
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

    # Before request handler to set g.lang_code
    @app.before_request
    def before_request():
        g.lang_code = get_locale()
        logger.debug(f"Current language code set to: {g.lang_code}")

    # Context processors
    @app.context_processor
    def inject_year():
        return {'current_year': datetime.utcnow().year}

    @app.context_processor
    def inject_languages():
        return {
            'languages': [
                ('en', 'English'),
                ('es', 'Español'),
                ('fr', 'Français')
            ]
        }

    # Load user
    from models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app
