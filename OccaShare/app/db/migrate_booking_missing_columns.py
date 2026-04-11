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
    columns_to_add = [
        ("actual_cost", "FLOAT DEFAULT 0.0"),
        ("balance_proof_url", "VARCHAR"),
        ("ocr_verified", "BOOLEAN DEFAULT FALSE"),
        ("liveness_verified", "BOOLEAN DEFAULT FALSE"),
        ("expires_at", "TIMESTAMP WITH TIME ZONE"),
        ("balance_due_date", "TIMESTAMP WITH TIME ZONE"),
        ("reservation_fee", "DECIMAL")
    ]

    with engine.connect() as conn:
        print("Migrating bookings table...")
        for col_name, col_type in columns_to_add:
            try:
                # Check if column exists
                check_sql = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='bookings' AND column_name='{col_name}'")
                result = conn.execute(check_sql).fetchone()
                
                if not result:
                    print(f"Adding column {col_name}...")
                    conn.execute(text(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"Successfully added {col_name}.")
                else:
                    print(f"Column {col_name} already exists.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                conn.rollback()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
