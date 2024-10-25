import os
import sys
from app import create_app, db
from models import User

def create_admin_user():
    app = create_app()
    with app.app_context():
        try:
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
            print(f"Error creating admin user: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    create_admin_user()
