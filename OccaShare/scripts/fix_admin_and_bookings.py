from sqlalchemy import create_engine, text
import sys
import os

# Add the project root to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Fixing admin user role...")
        try:
            conn.execute(text("UPDATE users SET role = 'admin' WHERE email = 'admin@occaserve.com';"))
            conn.commit()
            print("Successfully updated admin user role.")
        except Exception as e:
            print(f"Error updating admin role: {e}")
            conn.rollback()

        print("Adding missing columns to 'bookings' table...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS total_price FLOAT;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reservation_fee DECIMAL;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS balance_proof_url VARCHAR;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS balance_due_date TIMESTAMP WITH TIME ZONE;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS event_location TEXT;"))

            conn.commit()
            print("Successfully added missing columns to bookings.")
        except Exception as e:
            print(f"Error adding columns to bookings: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
