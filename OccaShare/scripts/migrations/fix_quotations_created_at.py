import sys
import os
from sqlalchemy import text

# Add the project root to sys.path to allow importing from app
# Since this is in scripts/migrations/, we need to go up two levels
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.db.database import engine

def apply_fix():
    print("Applying fix to add 'created_at' column to 'quotations' table...")
    try:
        with engine.connect() as connection:
            connection.execute(text("ALTER TABLE quotations ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"))
            connection.commit()
        print("Success: 'created_at' column added to 'quotations' table.")
    except Exception as e:
        print(f"Error: Could not add column: {e}")

if __name__ == "__main__":
    apply_fix()
