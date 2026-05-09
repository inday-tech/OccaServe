from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        print("Checking for status_reason column in users table...")
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='status_reason'"))
        if not res.fetchone():
            print("Adding status_reason column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN status_reason TEXT"))
            conn.commit()
            print("status_reason column added.")
        else:
            print("status_reason column already exists.")

        print("Checking for investigation_notes column in users table...")
        res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='investigation_notes'"))
        if not res.fetchone():
            print("Adding investigation_notes column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN investigation_notes TEXT"))
            conn.commit()
            print("investigation_notes column added.")
        else:
            print("investigation_notes column already exists.")

if __name__ == "__main__":
    migrate()
