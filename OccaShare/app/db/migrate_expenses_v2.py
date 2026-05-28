from sqlalchemy import text
import sys
import os

# Add the project root to sys.path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.database import engine, Base
from app.db.models import BookingExpense, BusinessExpense

def migrate():
    print("Creating new tables...")
    Base.metadata.create_all(engine, tables=[
        BookingExpense.__table__, 
        BusinessExpense.__table__
    ])
    print("Tables created successfully.")
    
    with engine.connect() as conn:
        print("Migrating 'bookings' table...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN booking_source VARCHAR DEFAULT 'OccaServe';"))
            conn.commit()
            print("Successfully added 'booking_source' column to 'bookings' table.")
        except Exception as e:
            print(f"Error or column already exists: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
