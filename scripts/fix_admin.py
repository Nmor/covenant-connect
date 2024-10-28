from app import create_app, db
from models import User

app = create_app()
with app.app_context():
    # Delete existing admin user
    admin = User.query.filter_by(username='admin').first()
    if admin:
        db.session.delete(admin)
        db.session.commit()
    
    # Create new admin user
    new_admin = User(
        username='admin',
        email='admin@example.com',
        is_admin=True
    )
    new_admin.set_password('admin123')
    db.session.add(new_admin)
    db.session.commit()
    print("Admin user recreated successfully!")
