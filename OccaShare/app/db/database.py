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
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_ref VARCHAR;",
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS customer_ref VARCHAR;",
        """
        UPDATE bookings b
        SET booking_ref = CONCAT(
            CASE 
                WHEN LENGTH(REGEXP_REPLACE(cp.business_name, '[^A-Za-z]', '', 'g')) >= 3 
                THEN UPPER(SUBSTRING(REGEXP_REPLACE(cp.business_name, '[^A-Za-z]', '', 'g') FROM 1 FOR 3)) 
                ELSE 'BK' 
            END, 
            '-', 
            LPAD(b.id::text, 3, '0')
        )
        FROM caterer_profiles cp
        WHERE b.caterer_id = cp.id AND (b.booking_ref IS NULL OR b.booking_ref = '' OR b.booking_ref LIKE 'BK-%');
        """,
        """
        UPDATE bookings b
        SET customer_ref = CONCAT(
            CASE 
                WHEN LENGTH(REGEXP_REPLACE(cp.business_name, '[^A-Za-z]', '', 'g')) >= 3 
                THEN UPPER(SUBSTRING(REGEXP_REPLACE(cp.business_name, '[^A-Za-z]', '', 'g') FROM 1 FOR 3)) 
                ELSE 'BK' 
            END, 
            '-C-', 
            LPAD(b.id::text, 3, '0')
        )
        FROM caterer_profiles cp
        WHERE b.caterer_id = cp.id AND (b.customer_ref IS NULL OR b.customer_ref = '' OR b.customer_ref LIKE 'WALKIN-BK-%' OR b.customer_ref LIKE 'CUST-%');
        """,
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
        """,
        """
        UPDATE catering_packages
        SET price_per_head = CASE 
                WHEN price_per_head IS NOT NULL AND price_per_head > 0 THEN price_per_head
                WHEN price IS NOT NULL AND price > 0 THEN price
                WHEN min_contract_amount IS NOT NULL AND min_contract_amount > 0 THEN min_contract_amount
                ELSE 350.0 
            END,
            price = CASE 
                WHEN price IS NOT NULL AND price > 0 THEN price
                WHEN price_per_head IS NOT NULL AND price_per_head > 0 THEN price_per_head
                WHEN min_contract_amount IS NOT NULL AND min_contract_amount > 0 THEN min_contract_amount
                ELSE 350.0 
            END
        WHERE pricing_mode = 'customizable' AND (price_per_head IS NULL OR price_per_head = 0);
        """,
        """
        UPDATE bookings b
        SET package_id = cp.id
        FROM catering_packages cp
        WHERE b.caterer_id = cp.caterer_id
          AND cp.pricing_mode = 'customizable'
          AND (b.package_id IS NULL OR b.package_id = 0)
          AND (
              b.is_custom_event = TRUE
              OR (b.custom_requirements IS NOT NULL AND b.custom_requirements->>'package_type' = 'customizable')
              OR (b.custom_requirements IS NOT NULL AND b.custom_requirements->>'customization' IS NOT NULL)
              OR (b.custom_requirements IS NOT NULL AND (b.custom_requirements->>'package_id')::text = cp.id::text)
              OR b.event_type ILIKE '%custom%'
              OR (
                  SELECT COUNT(*) 
                  FROM catering_packages cp2 
                  WHERE cp2.caterer_id = b.caterer_id AND cp2.status != 'archived'
              ) = 1
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
