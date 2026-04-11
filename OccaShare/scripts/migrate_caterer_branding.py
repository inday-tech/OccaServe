from sqlalchemy import create_engine, text
import sys
import os

# Add the project root to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding branding color columns to 'caterer_profiles'...")
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS primary_color VARCHAR DEFAULT '#2D3748';"))
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS secondary_color VARCHAR DEFAULT '#4A5568';"))
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS accent_color VARCHAR DEFAULT '#48BB78';"))
            conn.commit()
            print("Successfully added branding color columns.")
        except Exception as e:
            print(f"Error adding branding color columns: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
