import os
import sys
from pathlib import Path

# Add the parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app import create_app, db

def reset_database():
    app = create_app()
    with app.app_context():
        # Drop all tables
        db.drop_all()
        print("All tables dropped successfully")
        
        # Recreate all tables
        db.create_all()
        print("All tables recreated successfully")

if __name__ == "__main__":
    reset_database()
