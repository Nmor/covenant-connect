import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from models import User, PrayerRequest, Event, Sermon, Gallery, Donation, Settings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

def init_db():
    app = create_app()
    with app.app_context():
        try:
            # Create tables without dropping existing ones
            print("Checking and creating missing tables...")
            db.create_all()
            db.session.commit()
            print("Database tables verification completed")
            
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                print("Creating admin user...")
                # Create admin user
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    is_admin=True,
                    locale='en',
                    notification_preferences={
                        'prayer_requests': True,
                        'events': True,
                        'sermons': True,
                        'donations': True,
                        'news': True,
                        'desktop': True,
                        'email': True
                    }
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully")
            else:
                print("Admin user already exists")

            print("Database initialization completed successfully")
            
        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            db.session.rollback()
            sys.exit(1)
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    init_db()
