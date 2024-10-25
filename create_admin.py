import os
from app import create_app, db
from models import User

def create_admin_user():
    app = create_app()
    with app.app_context():
        # Create a test admin user if not exists
        admin_email = os.environ.get('MAIL_USERNAME')
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                username='admin',
                email=admin_email,
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully")
        else:
            print("Admin user already exists")

if __name__ == '__main__':
    create_admin_user()
