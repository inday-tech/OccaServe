from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Re-using the logic from existing migrations in the project
load_dotenv()

# Database credentials (from env)
hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "2004")
port_id = os.getenv("DB_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def add_column_if_not_exists(conn, table_name, column_name, column_type):
    check_sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' AND column_name='{column_name}'")
    result = conn.execute(check_sql).fetchone()
    if not result:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
        print(f"Added {column_name} to {table_name}")
    else:
        print(f"{column_name} already exists in {table_name}")

def migrate():
    with engine.connect() as conn:
        print("Migrating Item Ratings & Caching...")
        try:
            # 1. Update Review table
            add_column_if_not_exists(conn, 'reviews', 'food_quality_rating', 'INTEGER NULL')
            add_column_if_not_exists(conn, 'reviews', 'service_quality_rating', 'INTEGER NULL')
            add_column_if_not_exists(conn, 'reviews', 'timeliness_rating', 'INTEGER NULL')

            # 2. Add Caching Fields to Menu, Equipment, Services
            tables_to_update = ['menu_items', 'equipment', 'services']
            for table in tables_to_update:
                add_column_if_not_exists(conn, table, 'average_rating', 'FLOAT DEFAULT 0.0')
                add_column_if_not_exists(conn, table, 'review_count', 'INTEGER DEFAULT 0')

            # 3. Create ItemRating table if not exists
            create_item_ratings_sql = text("""
                CREATE TABLE IF NOT EXISTS item_ratings (
                    id SERIAL PRIMARY KEY,
                    review_id INTEGER REFERENCES reviews(id) ON DELETE CASCADE,
                    item_type VARCHAR(255),
                    item_id INTEGER,
                    rating INTEGER
                )
            """)
            conn.execute(create_item_ratings_sql)
            
            # Add indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_item_ratings_id ON item_ratings(id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_item_ratings_review_id ON item_ratings(review_id)"))
            
            conn.commit()
            print("Successfully migrated ratings.")
        except Exception as e:
            print(f"Error during migration: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
