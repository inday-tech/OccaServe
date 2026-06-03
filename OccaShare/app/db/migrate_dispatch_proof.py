import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def upgrade():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.begin() as conn:
        print("Adding dispatch_proof_url to bookings table...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN dispatch_proof_url VARCHAR"))
            print("Successfully added dispatch_proof_url!")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                print("Column dispatch_proof_url already exists. Skipping.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    upgrade()
