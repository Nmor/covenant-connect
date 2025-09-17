import logging
from datetime import datetime

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Application factory used by the tests."""
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    app.task_queue = None

    from models import User  # pylint: disable=import-outside-toplevel

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:  # type: ignore[name-defined]
        if not user_id:
            return None
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @app.context_processor
    def inject_year() -> dict[str, int]:
        return {'current_year': datetime.utcnow().year}

    from routes.auth import auth_bp  # pylint: disable=import-outside-toplevel
    from routes.donations import donations_bp  # pylint: disable=import-outside-toplevel
    from routes.events import events_bp  # pylint: disable=import-outside-toplevel
    from routes.home import home_bp  # pylint: disable=import-outside-toplevel
    from routes.internal import internal_bp  # pylint: disable=import-outside-toplevel
    from routes.prayers import prayers_bp  # pylint: disable=import-outside-toplevel
    from routes.sermons import sermons_bp  # pylint: disable=import-outside-toplevel

    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(internal_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(prayers_bp)
    app.register_blueprint(sermons_bp)

    return app
