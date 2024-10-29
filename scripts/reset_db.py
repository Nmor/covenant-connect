import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app, db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

def reset_db():
    app = create_app()
    with app.app_context():
        try:
            # Drop all tables if they exist
            print("Dropping all tables...")
            db.session.execute(text('DROP SCHEMA public CASCADE;'))
            db.session.execute(text('CREATE SCHEMA public;'))
            db.session.execute(text('GRANT ALL ON SCHEMA public TO postgres;'))
            db.session.execute(text('GRANT ALL ON SCHEMA public TO public;'))
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
