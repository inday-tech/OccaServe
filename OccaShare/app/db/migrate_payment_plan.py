from sqlalchemy import text
import sys
import os

# Add the project root to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.database import engine

def migrate():
    with engine.connect() as conn:
        print("Migrating 'bookings' table...")
        # Check if column exists first (optional but safe)
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN payment_plan VARCHAR DEFAULT 'downpayment';"))
            conn.commit()
            print("Successfully added 'payment_plan' column to 'bookings' table.")
        except Exception as e:
            print(f"Error or column already exists: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
