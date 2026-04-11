from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def add_price_column():
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")

    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        print("Adding 'price' column to 'menu_items' table...")
        try:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN price FLOAT DEFAULT 0.0;"))
            conn.commit()
            print("Successfully added 'price' column.")
        except Exception as e:
            if "already exists" in str(e):
                print("Note: 'price' column already exists.")
            else:
                print(f"Error adding 'price' column: {e}")
            conn.rollback()

if __name__ == "__main__":
    add_price_column()
