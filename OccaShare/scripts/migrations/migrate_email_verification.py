from app.database import SessionLocal
from sqlalchemy import text

def migrate_email_verification():
    db = SessionLocal()
    try:
        sql_statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_code VARCHAR(10)"
        ]
        
        for sql in sql_statements:
            print(f"Executing: {sql}")
            db.execute(text(sql))
            
        # Optional: Set existing users as verified so they are not locked out
        print("Setting existing users as verified...")
        db.execute(text("UPDATE users SET is_email_verified = TRUE WHERE is_email_verified IS FALSE"))
            
        db.commit()
        print("Email Verification migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_email_verification()
