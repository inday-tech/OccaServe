"""Store customer event venue address components separately."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.db.database import SessionLocal


def run():
    db = SessionLocal()
    try:
        for column, column_type in (
            ("venue_street", "TEXT"),
            ("venue_landmark", "TEXT"),
            ("venue_barangay", "VARCHAR"),
            ("venue_city", "VARCHAR"),
            ("venue_province", "VARCHAR"),
        ):
            db.execute(text(
                f"ALTER TABLE bookings ADD COLUMN IF NOT EXISTS {column} {column_type}"
            ))
        db.commit()
        print("OK: Booking event address component columns are available.")
    except Exception as error:
        db.rollback()
        print(f"FAILED: Booking event address component migration failed: {error}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
