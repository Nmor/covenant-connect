import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db


def reset_db():
    app = create_app()
    with app.app_context():
        try:
            # Drop all existing tables
            print("Dropping all tables...")
            db.drop_all()
            db.session.commit()
            print("All tables dropped successfully")
            
            # Create all tables
            print("Creating tables...")
            db.create_all()
            db.session.commit()
            print("Tables created successfully")
            
        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            db.session.rollback()
            sys.exit(1)
        except Exception as e:
            print(f"Error resetting database: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    reset_db()
