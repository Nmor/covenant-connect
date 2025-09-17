import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging

from app import create_app, db
from models import User

logger = logging.getLogger('covenant_connect')

def fix_admin():
    app = create_app()
    with app.app_context():
        try:
            # Delete existing admin if exists
            admin = User.query.filter_by(email='admin@covenantconnect.com').first()
            if admin:
                db.session.delete(admin)
                logger.info("Deleted existing admin user")
            
            # Create new admin user
            admin = User(
                username='admin',
                email='admin@covenantconnect.com',
                is_admin=True,
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
            logger.info("Admin user created successfully!")
            print("Admin user setup completed successfully!")
            
        except Exception as e:
            logger.error(f"Error setting up admin user: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    fix_admin()
