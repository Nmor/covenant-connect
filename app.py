from flask import Flask, render_template, request, g, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_babel import Babel
from flask_sse import sse
import os
from datetime import datetime

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
babel = Babel()

def get_locale():
    # First try to get locale from query parameter
    locale = request.args.get('lang')
    if locale in ['en', 'es', 'fr']:
        session['lang'] = locale
        return locale
        
    # Then try to get locale from user preferences if logged in
    if hasattr(g, 'user') and g.user and g.user.locale:
        return g.user.locale
        
    # Then try to get locale from session
    if 'lang' in session:
        return session['lang']
        
    # Finally, fall back to browser's preferred language
    return request.accept_languages.best_match(['en', 'es', 'fr'])

def create_app():
    app = Flask(__name__)
    
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

    # SSE configuration
    app.config["REDIS_URL"] = "memory://"
    app.register_blueprint(sse, url_prefix='/stream')

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
