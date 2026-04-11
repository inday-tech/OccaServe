import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Mirrored fallback logic from app/db/database.py
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
else:
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        print("Adding signature columns to quotations table...")
        
        columns_to_add = [
            ("caterer_signature", "TEXT"),
            ("customer_signature", "TEXT"),
            ("caterer_signed_at", "TIMESTAMP WITH TIME ZONE"),
            ("customer_signed_at", "TIMESTAMP WITH TIME ZONE")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                # Check if column exists first
                check_query = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='quotations' AND column_name='{col_name}';")
                result = conn.execute(check_query).fetchone()
                
                if not result:
                    print(f"Adding column: {col_name}")
                    conn.execute(text(f"ALTER TABLE quotations ADD COLUMN {col_name} {col_type};"))
                    # No need for explicit commit if autocommit is on, but modern SQLAlchemy requires it for migrations usually
                    conn.commit()
                else:
                    print(f"Column {col_name} already exists.")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")

if __name__ == "__main__":
    migrate()
    print("Migration complete.")
