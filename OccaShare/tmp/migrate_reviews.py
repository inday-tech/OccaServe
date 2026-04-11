import sys
import os
from sqlalchemy import create_engine, text

# Add the project root to the python path to import app.db.database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        # Check if the column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='reviews' AND column_name='is_highlighted';
        """)
        result = connection.execute(check_query).fetchone()
        
        if not result:
            print("Adding 'is_highlighted' column to 'reviews' table...")
            connection.execute(text("ALTER TABLE reviews ADD COLUMN is_highlighted BOOLEAN DEFAULT FALSE;"))
            connection.commit()
            print("Migration successful.")
        else:
            print("'is_highlighted' column already exists.")

if __name__ == "__main__":
    migrate()
