from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL, engine
from app.db.models import Base

def migrate():
    # 1. Create new tables
    print("Creating new tables (if they don't exist)...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Add new columns to existing tables
    with engine.connect() as conn:
        print("Adding 'is_kyc_complete' to 'users'...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_kyc_complete BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added 'is_kyc_complete'.")
        except Exception as e:
            print(f"Note: 'is_kyc_complete' might already exist or error occurred: {e}")
            conn.rollback()

        print("Adding new columns to 'bookings'...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN expires_at TIMESTAMPTZ;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN reservation_fee DECIMAL;"))
            conn.commit()
            print("Successfully added booking columns.")
        except Exception as e:
            print(f"Note: Booking columns might already exist or error occurred: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
