from sqlalchemy import create_engine, text
from app.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Checking for missing columns in 'bookings' table...")
        
        # Add payment_method
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN payment_method VARCHAR;"))
            print("Added column: payment_method")
        except Exception as e:
            print(f"Column payment_method might already exist or error: {e}")
            
        # Add ocr_verified
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN ocr_verified BOOLEAN DEFAULT FALSE;"))
            print("Added column: ocr_verified")
        except Exception as e:
            print(f"Column ocr_verified might already exist or error: {e}")
            
        # Add liveness_verified
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN liveness_verified BOOLEAN DEFAULT FALSE;"))
            print("Added column: liveness_verified")
        except Exception as e:
            print(f"Column liveness_verified might already exist or error: {e}")
            
        conn.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
