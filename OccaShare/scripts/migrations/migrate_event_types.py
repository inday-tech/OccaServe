from app.database import SessionLocal
from sqlalchemy import text

def migrate_caterer_profiles():
    db = SessionLocal()
    try:
        # PostgreSQL syntax for adding an array column if it doesn't exist
        sql = "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS event_types TEXT[]"
        print(f"Executing: {sql}")
        db.execute(text(sql))
        db.commit()
        print("Migration successful: Added event_types column to caterer_profiles.")
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_caterer_profiles()
