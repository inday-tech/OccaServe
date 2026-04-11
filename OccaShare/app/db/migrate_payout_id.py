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

def migrate():
    with engine.connect() as conn:
        print("Adding payout_id column to bookings table...")
        try:
            # First check if the column exists to avoid error
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='bookings' AND column_name='payout_id'")
            result = conn.execute(check_sql).fetchone()
            
            if not result:
                conn.execute(text("ALTER TABLE bookings ADD COLUMN payout_id INTEGER REFERENCES payouts(id)"))
                conn.commit()
                print("Successfully added payout_id column.")
            else:
                print("Column payout_id already exists.")
        except Exception as e:
            print(f"Error adding column: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
