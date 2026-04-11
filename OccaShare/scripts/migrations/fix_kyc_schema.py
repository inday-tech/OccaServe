import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.database import engine
from sqlalchemy import text

def run_fix():
    with engine.connect() as conn:
        print("Altering 'identity_verifications' table...")
        try:
            conn.execute(text("ALTER TABLE identity_verifications ALTER COLUMN selfie_url DROP NOT NULL;"))
            conn.commit()
            print("Successfully dropped NOT NULL constraint from 'selfie_url'.")
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()

if __name__ == "__main__":
    run_fix()
