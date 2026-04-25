import sys
import os

# Ensure the correct path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.db.database import engine
from sqlalchemy import text

def run_migration():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE ingredients ADD COLUMN is_archived BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added is_archived to ingredients.")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("Column is_archived already exists.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    run_migration()
