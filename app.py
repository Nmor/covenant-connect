import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "default-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Register blueprints
    from routes.home import home_bp
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.events import events_bp
    from routes.gallery import gallery_bp
    from routes.prayers import prayers_bp
    from routes.donations import donations_bp
    
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(prayers_bp)
    app.register_blueprint(donations_bp)

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            app.logger.error(f"Error loading user: {e}")
            return None
    
    return app

def init_db(app):
    # Create database tables
    try:
        with app.app_context():
            db.create_all()
            app.logger.info("Database tables created successfully")
    except Exception as e:
        app.logger.error(f"Error creating database tables: {e}")
        raise

if __name__ == '__main__':
    app = create_app()
    init_db(app)
    app.run(host='0.0.0.0', port=5000)
