import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)

# Primary connection string
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def run_migration():
    with engine.begin() as conn:
        print("Starting Phase 3 Database Migration...")
        
        # 1. Add missing columns to bookings
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN is_custom_event BOOLEAN DEFAULT FALSE;"))
            print("Added is_custom_event to bookings")
        except Exception as e:
            print("is_custom_event might already exist:", e)

        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN custom_requirements JSONB;"))
            print("Added custom_requirements to bookings")
        except Exception as e:
            print("custom_requirements might already exist:", e)

        print("Phase 3 Database Migration Complete!")

if __name__ == "__main__":
    run_migration()
