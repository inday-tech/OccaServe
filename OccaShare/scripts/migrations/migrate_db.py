from app.database import SessionLocal
from sqlalchemy import text

def migrate_bookings_table():
    db = SessionLocal()
    try:
        # Check if columns exist, if not add them
        # simple way: try to add, ignore if error? or check Info schema. 
        # easiest in postgres is "ADD COLUMN IF NOT EXISTS"
        
        sql_statements = [
            "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50) DEFAULT 'pending'",
            "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS ocr_verified BOOLEAN DEFAULT FALSE",
            "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS liveness_verified BOOLEAN DEFAULT FALSE"
        ]
        
        for sql in sql_statements:
            print(f"Executing: {sql}")
            db.execute(text(sql))
            
        db.commit()
        print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_bookings_table()
