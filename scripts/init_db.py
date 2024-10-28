import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models import User, PrayerRequest, Event, Sermon, Gallery, Donation, Settings

def init_db():
    app = create_app()
    with app.app_context():
        try:
            # Drop all existing tables
            db.drop_all()
            print("All tables dropped successfully")
            
            # Create all tables fresh
            db.create_all()
            print("All tables created successfully")
            
            # Create initial settings
            settings = Settings(
                business_name="Covenant Connect",
                theme_preference="dark",
                addresses=[],
                social_media_links={},
                contact_info={}
            )
            db.session.add(settings)
            db.session.commit()
            print("Initial settings created")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    init_db()
