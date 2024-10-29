from app import create_app, db
from models import User

def create_admin():
    app = create_app()
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@covenantconnect.com').first()
        if admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@covenantconnect.com',
            is_admin=True,
            notification_preferences={}
        )
        admin.set_password('admin123')  # This should be changed after first login
        
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")

if __name__ == "__main__":
    create_admin()
