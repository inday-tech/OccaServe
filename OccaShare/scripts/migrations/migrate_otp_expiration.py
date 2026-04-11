from app.database import SessionLocal
from sqlalchemy import text
from datetime import datetime

def migrate_otp_expiration():
    db = SessionLocal()
    try:
        sql_statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMP WITH TIME ZONE"
        ]
        
        for sql in sql_statements:
            print(f"Executing: {sql}")
            db.execute(text(sql))
            
        db.commit()
        print("OTP Expiration migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_otp_expiration()
