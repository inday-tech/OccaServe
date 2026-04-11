from app.database import SessionLocal
from sqlalchemy import text

def migrate_users_table():
    db = SessionLocal()
    try:
        sql_statements = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255) UNIQUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS instagram_id VARCHAR(255) UNIQUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(50) DEFAULT 'email'"
        ]
        
        for sql in sql_statements:
            print(f"Executing: {sql}")
            db.execute(text(sql))
            
        db.commit()
        print("User table migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_users_table()
