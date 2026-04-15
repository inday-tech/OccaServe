import sys
import os

# Add parent dir to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import text
from app.db.database import engine
from app.db import models

def migrate():
    with engine.connect() as conn:
        print("Adding JSONB columns for Detailed ROI...")
        
        try:
            conn.execute(text("ALTER TABLE catering_packages ADD COLUMN cost_breakdown JSONB;"))
            conn.commit()
            print("Added cost_breakdown to catering_packages.")
        except Exception as e:
            print(f"cost_breakdown might already exist in catering_packages: {e}")
            
        try:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN cost_breakdown JSONB;"))
            conn.commit()
            print("Added cost_breakdown to menu_items.")
        except Exception as e:
            print(f"cost_breakdown might already exist in menu_items: {e}")

        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN actual_cost_breakdown JSONB;"))
            conn.commit()
            print("Added actual_cost_breakdown to bookings.")
        except Exception as e:
            print(f"actual_cost_breakdown might already exist in bookings: {e}")

        models.Base.metadata.create_all(bind=engine)
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
