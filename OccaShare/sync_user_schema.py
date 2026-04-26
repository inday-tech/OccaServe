import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

engine = create_engine(DATABASE_URL)

def sync_schema():
    with engine.connect() as conn:
        print("Checking 'users' table columns via SQLAlchemy...")
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"))
        columns = [row[0] for row in result]
        print(f"Columns: {columns}")
        
        needed = ['middle_name', 'dob', 'facebook_id', 'google_id', 'instagram_id', 'is_email_verified']
        for col in needed:
            if col not in columns:
                print(f"Missing {col}, adding...")
                if col == 'dob':
                    conn.execute(text("ALTER TABLE users ADD COLUMN dob DATE NULL"))
                elif col == 'middle_name':
                    conn.execute(text("ALTER TABLE users ADD COLUMN middle_name VARCHAR(255) NULL"))
                elif col.endswith('_id'):
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} VARCHAR(255) NULL"))
                elif col.startswith('is_'):
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print(f"Added {col}")
            else:
                print(f"{col} already exists.")

if __name__ == "__main__":
    sync_schema()
