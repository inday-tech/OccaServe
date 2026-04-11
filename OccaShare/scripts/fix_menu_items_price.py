from sqlalchemy import create_engine, text
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding missing 'price' column to 'menu_items' table...")
        try:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS price FLOAT DEFAULT 0.0;"))
            conn.commit()
            print("Successfully added price column to menu_items.")
        except Exception as e:
            print(f"Error adding columns to menu_items: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
