import sys
import os
from sqlalchemy import text

# Add the project root to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import engine

def apply_migration():
    migration_file = os.path.join(os.path.dirname(__file__), 'migrate_caterer_fields.sql')
    
    if not os.path.exists(migration_file):
        print(f"Error: Migration file not found at {migration_file}")
        return

    print(f"Reading migration script from {migration_file}...")
    with open(migration_file, 'r') as f:
        sql = f.read()

    print("Connecting to database and applying migration...")
    try:
        with engine.connect() as connection:
            # SQLAlchemy connection doesn't support multiple statements in one execute() easily 
            # for some dialects, so we split by semicolon
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for statement in statements:
                print(f"Executing: {statement[:50]}...")
                connection.execute(text(statement))
            connection.commit()
        print("Migration applied successfully!")
    except Exception as e:
        print(f"An error occurred while applying the migration: {e}")

if __name__ == "__main__":
    apply_migration()
