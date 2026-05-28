import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.database import engine
from sqlalchemy import text

def force_sync():
    try:
        with engine.begin() as conn:
            print(f"Syncing with: {engine.url}")
            
            # Check for middle_initial
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'middle_initial'"))
            if not res.fetchone():
                print("middle_initial missing, adding...")
                conn.execute(text("ALTER TABLE users ADD COLUMN middle_initial VARCHAR(1) NULL"))
                print("Added middle_initial")
            else:
                print("middle_initial already exists")

            # Check for middle_name (since user seems to want it back too?)
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'middle_name'"))
            if not res.fetchone():
                print("middle_name missing, adding...")
                conn.execute(text("ALTER TABLE users ADD COLUMN middle_name VARCHAR(255) NULL"))
                print("Added middle_name")
            else:
                print("middle_name already exists")

            # Check for booking_source in bookings
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'bookings' AND column_name = 'booking_source'"))
            if not res.fetchone():
                print("booking_source missing from bookings table, adding...")
                conn.execute(text("ALTER TABLE bookings ADD COLUMN booking_source VARCHAR(255) DEFAULT 'OccaServe'"))
                print("Added booking_source")
            else:
                print("booking_source already exists")
                
            print("Sync complete.")
    except Exception as e:
        print(f"Error during sync: {e}")

if __name__ == "__main__":
    force_sync()
