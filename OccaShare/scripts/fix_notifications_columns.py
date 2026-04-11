from sqlalchemy import create_engine, text
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding missing 'link' column to 'notifications' table...")
        try:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS link VARCHAR;"))
            conn.commit()
            print("Successfully added link column to notifications.")
        except Exception as e:
            print(f"Error adding columns to notifications: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
