import sys
import os

# Add the project root to sys.path
sys.path.append(r'c:\Projects\OccaShare')

from app.db.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as connection:
        # Add caterer_reply column
        try:
            connection.execute(text("ALTER TABLE reviews ADD COLUMN caterer_reply TEXT"))
            connection.commit()
            print("Successfully added caterer_reply column.")
        except Exception as e:
            print(f"Error adding caterer_reply: {e}")
            connection.rollback()

        # Add is_helpful column
        try:
            connection.execute(text("ALTER TABLE reviews ADD COLUMN is_helpful BOOLEAN DEFAULT FALSE"))
            connection.commit()
            print("Successfully added is_helpful column.")
        except Exception as e:
            print(f"Error adding is_helpful: {e}")
            connection.rollback()

if __name__ == "__main__":
    migrate()
