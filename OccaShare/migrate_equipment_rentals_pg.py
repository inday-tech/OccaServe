from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv(override=True)

hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "2004")
port = os.getenv("DB_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port}/{database}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def add_column(engine, table, column_def):
    with engine.begin() as conn:
        try:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))
            print(f"Added {column_def} to {table}")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print(f"Column already exists: {column_def}")
            else:
                print(f"Error adding {column_def}: {e}")

if __name__ == "__main__":
    # Equipment Fields
    add_column(engine, "equipment", "security_deposit_pct FLOAT DEFAULT 20.0")
    add_column(engine, "equipment", "maintenance_buffer_hours INTEGER DEFAULT 12")
    add_column(engine, "equipment", "requires_kyc BOOLEAN DEFAULT FALSE")

    # Booking Fields
    add_column(engine, "bookings", "security_deposit_amount FLOAT DEFAULT 0.0")
    add_column(engine, "bookings", "security_deposit_status VARCHAR DEFAULT 'unpaid'")
    add_column(engine, "bookings", "damage_deduction_amount FLOAT DEFAULT 0.0")
    add_column(engine, "bookings", "missing_items_count INTEGER DEFAULT 0")
    add_column(engine, "bookings", "release_photo_url VARCHAR")
    add_column(engine, "bookings", "return_photo_url VARCHAR")
    add_column(engine, "bookings", "damage_proof_url VARCHAR")
    add_column(engine, "bookings", "rental_disputed BOOLEAN DEFAULT FALSE")

    print("Migration finished!")
