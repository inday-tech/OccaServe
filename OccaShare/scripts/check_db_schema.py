from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def check_columns():
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")

    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    tables = ["menu_items", "catering_packages"]
    
    with engine.connect() as conn:
        for table in tables:
            print(f"\nColumns in '{table}':")
            result = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}';"))
            for row in result:
                print(f"  - {row[0]} ({row[1]})")

if __name__ == "__main__":
    check_columns()
