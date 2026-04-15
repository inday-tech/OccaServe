import os
import sys
from sqlalchemy import text
# Add the root directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.database import engine

def migrate():
    print("Starting migration to add payment verification columns...")
    
    with engine.connect() as connection:
        # 1. Add payment_verification_data (JSONB)
        try:
            connection.execute(text("ALTER TABLE bookings ADD COLUMN payment_verification_data JSONB;"))
            connection.commit()
            print("Successfully added column: payment_verification_data")
        except Exception as e:
            print(f"Error adding payment_verification_data (it might already exist): {e}")
            connection.rollback()

        # 2. Add proof_image_hash (String)
        try:
            connection.execute(text("ALTER TABLE bookings ADD COLUMN proof_image_hash VARCHAR;"))
            connection.commit()
            print("Successfully added column: proof_image_hash")
        except Exception as e:
            print(f"Error adding proof_image_hash (it might already exist): {e}")
            connection.rollback()

    print("Migration complete.")

if __name__ == "__main__":
    migrate()
