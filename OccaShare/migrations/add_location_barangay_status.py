"""Add explicit barangay-resolution status for business and event locations."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.db.database import SessionLocal


def run():
    db = SessionLocal()
    try:
        db.execute(text(
            "ALTER TABLE caterer_profiles "
            "ADD COLUMN IF NOT EXISTS barangay_status VARCHAR"
        ))
        db.execute(text(
            "ALTER TABLE bookings "
            "ADD COLUMN IF NOT EXISTS venue_barangay_status VARCHAR"
        ))
        db.commit()
        print("OK: Location barangay status columns are available.")
    except Exception as error:
        db.rollback()
        print(f"FAILED: Location barangay status migration failed: {error}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
