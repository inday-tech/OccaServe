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
        conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN terms_and_conditions TEXT;"))
        conn.commit()
        print("Successfully added terms_and_conditions to caterer_profiles")
except Exception as e:
    print(f"Error: {e}")
