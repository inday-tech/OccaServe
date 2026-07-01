"""
Migration: Add structured address columns to users table
Run: python migrations/add_user_structured_address.py
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import SessionLocal

def run():
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE users
                ADD COLUMN IF NOT EXISTS province VARCHAR,
                ADD COLUMN IF NOT EXISTS city_municipality VARCHAR,
                ADD COLUMN IF NOT EXISTS barangay VARCHAR,
                ADD COLUMN IF NOT EXISTS street_address TEXT;
        """))
        db.commit()
        print("OK: Migration complete: province, city_municipality, barangay, street_address added to users table.")
    except Exception as e:
        db.rollback()
        print(f"FAILED: Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run()
