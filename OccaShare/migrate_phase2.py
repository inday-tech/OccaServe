import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.db.database import engine
from sqlalchemy import text

def run_migration():
    print("Starting phase 2 migration...")
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE services ADD COLUMN category VARCHAR"))
            print("Added category column to services")
        except Exception as e:
            print(f"Column category may already exist: {e}")

        try:
            conn.execute(text("ALTER TABLE services ADD COLUMN image_url VARCHAR"))
            print("Added image_url column to services")
        except Exception as e:
            print(f"Column image_url may already exist: {e}")

    print("Phase 2 migration complete.")

if __name__ == "__main__":
    run_migration()
