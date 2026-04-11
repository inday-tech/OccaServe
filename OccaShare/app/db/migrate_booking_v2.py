from sqlalchemy import text
from .database import engine
from . import models

def migrate():
    # Raw SQL to add columns to existing bookings table
    with engine.connect() as conn:
        print("Adding columns to bookings table...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN total_price FLOAT;"))
            conn.commit()
        except Exception as e:
            print(f"total_price column might already exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN event_location TEXT;"))
            conn.commit()
        except Exception as e:
            print(f"event_location column might already exist: {e}")

        print("Creating booking_menu_items table...")
        # create_all will only create missing tables
        models.Base.metadata.create_all(bind=engine)
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
