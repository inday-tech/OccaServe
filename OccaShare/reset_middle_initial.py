import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.database import engine
from sqlalchemy import text

def reset_column():
    try:
        with engine.begin() as conn:
            print(f"Resetting column on: {engine.url}")
            
            # Try to drop if exists
            try:
                conn.execute(text("ALTER TABLE users DROP COLUMN middle_initial"))
                print("Dropped existing middle_initial")
            except:
                print("middle_initial did not exist or could not be dropped")
            
            # Add it
            conn.execute(text("ALTER TABLE users ADD COLUMN middle_initial VARCHAR(1) NULL"))
            print("Added middle_initial successfully")
            
            # Verify
            res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'middle_initial'"))
            if res.fetchone():
                print("Verification: middle_initial EXISTS now.")
            else:
                print("Verification: middle_initial still MISSING!")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_column()
