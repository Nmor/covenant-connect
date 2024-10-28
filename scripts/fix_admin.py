import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from models import User

def create_test_users():
    app = create_app()
    with app.app_context():
        try:
            # Delete all existing users
            User.query.delete()
            db.session.commit()
            
            # Create admin user
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            
            # Create test user
            test_user = User(
                username='testuser',
                email='test@example.com',
                is_admin=False
            )
            test_user.set_password('test123')
            
            db.session.add(admin)
            db.session.add(test_user)
            db.session.commit()
            print("Test users created successfully!")
            
        except Exception as e:
            print(f"Error creating users: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    create_test_users()
