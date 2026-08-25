import os
import sys
from sqlalchemy import text
from app.db.database import engine

def apply_migration():
    with engine.begin() as conn:
        # Find unique constraint on user_id
        result = conn.execute(text("""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'identity_verifications'::regclass
            AND contype = 'u'
        """))
        for row in result:
            print(f"Dropping constraint {row[0]}")
            conn.execute(text(f'ALTER TABLE identity_verifications DROP CONSTRAINT "{row[0]}"'))
        
        # Add new columns
        columns = [
            "booking_id INTEGER REFERENCES bookings(id)",
            "id_type VARCHAR",
            "id_expiry_date DATE",
            "ocr_status VARCHAR",
            "match_status VARCHAR",
            "verification_valid_until TIMESTAMP WITH TIME ZONE",
            "review_status VARCHAR",
            "reviewed_by INTEGER REFERENCES users(id)",
            "reviewed_at TIMESTAMP WITH TIME ZONE"
        ]
        
        for col in columns:
            col_name = col.split(' ')[0]
            try:
                conn.execute(text(f"ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS {col}"))
                print(f"Added {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")

if __name__ == '__main__':
    apply_migration()
