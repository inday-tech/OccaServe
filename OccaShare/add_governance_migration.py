import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "2004")
port_id = os.getenv("DB_PORT", "5432")

SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

from sqlalchemy import create_engine, text

engine = create_engine(SQLALCHEMY_DATABASE_URL)

try:
    with engine.connect() as conn:
        # Add new governance columns
        conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS booking_lead_time INTEGER DEFAULT 7;"))
        conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS min_pax INTEGER DEFAULT 20;"))
        
        # Drop redundant policy columns
        conn.execute(text("ALTER TABLE caterer_profiles DROP COLUMN IF EXISTS booking_policy;"))
        conn.execute(text("ALTER TABLE caterer_profiles DROP COLUMN IF EXISTS payment_policy;"))
        conn.execute(text("ALTER TABLE caterer_profiles DROP COLUMN IF EXISTS cancellation_policy;"))
        
        conn.commit()
        print("Successfully updated caterer_profiles schema (added governance, removed redundant policies).")
except Exception as e:
    print(f"Error: {e}")
