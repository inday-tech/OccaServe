import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding 'service_type' column to 'catering_packages'...")
        try:
            conn.execute(text("ALTER TABLE catering_packages ADD COLUMN service_type VARCHAR DEFAULT 'General';"))
            conn.commit()
            print("Successfully added 'service_type'.")
        except Exception as e:
            print(f"Error adding 'service_type': {e}")
            conn.rollback()

        print("Adding satisfaction columns to 'reviews'...")
        try:
            conn.execute(text("ALTER TABLE reviews ADD COLUMN recommend BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE reviews ADD COLUMN was_punctual BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added satisfaction columns.")
        except Exception as e:
            print(f"Error adding satisfaction columns: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
