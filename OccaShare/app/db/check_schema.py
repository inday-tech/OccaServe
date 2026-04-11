from sqlalchemy import create_engine, text, inspect
import os
from dotenv import load_dotenv

load_dotenv()

# Database credentials (from env)
hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "2004")
port_id = os.getenv("DB_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

def check_schema():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tables in database: {tables}")
    
    if "bookings" in tables:
        columns = [c["name"] for c in inspector.get_columns("bookings")]
        print(f"Columns in 'bookings': {columns}")
        
        required_columns = [
            "actual_cost", "total_price", "reservation_fee", 
            "balance_proof_url", "payout_id", "ocr_verified", 
            "liveness_verified", "expires_at", "balance_due_date", 
            "event_location"
        ]
        
        for col in required_columns:
            if col in columns:
                print(f"SUCCESS: '{col}' exists in 'bookings'.")
            else:
                print(f"MISSING: '{col}' is missing from 'bookings'.")
    else:
        print("MISSING: 'bookings' table does not exist.")

    for table in ["payouts", "payout_items"]:
        if table in tables:
            print(f"SUCCESS: '{table}' table exists.")
        else:
            print(f"MISSING: '{table}' table is missing.")

if __name__ == "__main__":
    check_schema()
