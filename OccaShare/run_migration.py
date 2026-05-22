import asyncio
from sqlalchemy import create_engine, text
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SQLALCHEMY_DATABASE_URL

def upgrade():
    print(f"Connecting to {SQLALCHEMY_DATABASE_URL}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN max_bookings_per_day INTEGER DEFAULT 1;"))
            print("Added max_bookings_per_day")
        except Exception as e:
            print("Could not add max_bookings_per_day", e)
            
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN auto_block_enabled BOOLEAN DEFAULT TRUE;"))
            print("Added auto_block_enabled")
        except Exception as e:
            print("Could not add auto_block_enabled", e)
        conn.commit()

if __name__ == "__main__":
    upgrade()
