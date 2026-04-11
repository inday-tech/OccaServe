import sys
import os
from sqlalchemy import create_engine, text

# Get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

try:
    from app.db.database import SQLALCHEMY_DATABASE_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
except ImportError:
    print("Error: Could not import app.db.database. Ensure you are running this from the project root.")
    sys.exit(1)

def migrate():
    with engine.connect() as conn:
        print("Starting reviews table migration...")
        
        columns = [
            ("is_highlighted", "BOOLEAN DEFAULT FALSE"),
            ("caterer_reply", "TEXT"),
            ("is_helpful", "BOOLEAN DEFAULT FALSE")
        ]
        
        for col_name, col_type in columns:
            print(f"Adding '{col_name}' column...")
            try:
                conn.execute(text(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Successfully added '{col_name}'.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"Column '{col_name}' already exists. Skipping.")
                else:
                    print(f"Error adding '{col_name}': {e}")
                conn.rollback()

        print("Migration complete!")

if __name__ == "__main__":
    migrate()
