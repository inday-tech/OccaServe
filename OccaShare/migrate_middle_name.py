import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.database import engine
from sqlalchemy import text

def migrate():
    try:
        with engine.begin() as conn:
            print(f"Migrating on: {engine.url}")
            
            # 1. Ensure middle_name exists and is VARCHAR (unlimited or 255)
            res = conn.execute(text("SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'middle_name'"))
            row = res.fetchone()
            if not row:
                print("middle_name missing, adding...")
                conn.execute(text("ALTER TABLE users ADD COLUMN middle_name VARCHAR(255) NULL"))
            else:
                print(f"middle_name exists: {row}")
                # If it was restricted (like if someone made it VARCHAR(1) by mistake), we fix it
                if row[2] == 1:
                    print("middle_name was VARCHAR(1), expanding to VARCHAR(255)...")
                    conn.execute(text("ALTER TABLE users ALTER COLUMN middle_name TYPE VARCHAR(255)"))

            print("Migration complete.")
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
