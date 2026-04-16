from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "1425")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def check_bookings_schema():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    table = "bookings"
    print(f"\nColumns in '{table}':")
    try:
        columns = inspector.get_columns(table)
        for column in columns:
            print(f" - {column['name']} ({column['type']})")
    except Exception as e:
        print(f"Error inspecting table '{table}': {e}")

if __name__ == "__main__":
    check_bookings_schema()
