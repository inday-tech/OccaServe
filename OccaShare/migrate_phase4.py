import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)

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
        print("Starting Phase 4 Database Migration...")
        
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS booking_messages (
                    id SERIAL PRIMARY KEY,
                    booking_id INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
                    sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    message TEXT,
                    attachment_url VARCHAR,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("Created booking_messages table")
        except Exception as e:
            print("Error creating booking_messages table:", e)

        print("Phase 4 Database Migration Complete!")

if __name__ == "__main__":
    run_migration()
