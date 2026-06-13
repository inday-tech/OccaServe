import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.db.database import SessionLocal
from sqlalchemy import text

def run_migration():
    db = SessionLocal()
    try:
        # Add booking_id column
        db.execute(text("ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS booking_id INTEGER REFERENCES bookings(id)"))
        # Add commission_rate column
        db.execute(text("ALTER TABLE billing_invoices ADD COLUMN IF NOT EXISTS commission_rate FLOAT DEFAULT 0.10"))
        
        db.commit()
        print("Migration successful: added booking_id and commission_rate to billing_invoices.")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
