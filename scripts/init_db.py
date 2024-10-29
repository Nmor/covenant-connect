import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from models import User

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
            
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    init_db()
