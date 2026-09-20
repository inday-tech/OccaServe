import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# load_dotenv() will NOT overwrite existing environment variables by default
load_dotenv(override=True)

# Check for various cloud environment indicators
IS_CLOUD = any(os.getenv(key) for key in ["RAILWAY_PROJECT_ID", "RENDER", "PORT"])

# Primary connection string
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    if IS_CLOUD:
        print("CRITICAL: Running in a cloud environment but DATABASE_URL is missing!")
        print("Please ensure you have set the DATABASE_URL variable in your Dashboard.")
    
    # Fallback to local development components
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
else:
    # Ensure compatible prefix
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Summary of target (redacted password)
target_log = SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL
print(f"DATABASE CONNECTION TARGET: {target_log}")

# Create engine with connection pooling for production stability
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Auto-sync critical missing columns on startup / import
def _ensure_schema_sync():
    from sqlalchemy import text
    sync_sqls = [
        "ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS entry_type VARCHAR DEFAULT 'system_change';",
        "ALTER TABLE booking_history ADD COLUMN IF NOT EXISTS communication_channel VARCHAR;",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS custom_name VARCHAR;",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS equipment_id INTEGER;",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS service_id INTEGER;",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS is_add_on BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE booking_menu_items ADD COLUMN IF NOT EXISTS choices JSONB;",
        "ALTER TABLE booking_contracts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE booking_contracts ADD COLUMN IF NOT EXISTS contract_history JSONB;",
        """
        CREATE TABLE IF NOT EXISTS booking_payment_records (
            id SERIAL PRIMARY KEY,
            booking_id INTEGER REFERENCES bookings(id) ON DELETE CASCADE,
            amount FLOAT NOT NULL,
            payment_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            payment_method VARCHAR,
            payment_type VARCHAR,
            reference_notes TEXT,
            recorded_by VARCHAR
        );
        """
    ]
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for sql in sync_sqls:
                try:
                    conn.execute(text(sql))
                except Exception:
                    pass
    except Exception as e:
        print(f"[DB AUTO-SYNC WARNING] {e}")

_ensure_schema_sync()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
