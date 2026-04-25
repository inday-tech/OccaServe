import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def upgrade():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    commands = [
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS internal_cost_per_pax FLOAT DEFAULT 0.0;",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS base_pax INTEGER DEFAULT 50;",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS labor_cost FLOAT DEFAULT 0.0;",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS utility_cost FLOAT DEFAULT 0.0;",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS equipment_cost FLOAT DEFAULT 0.0;",
        "ALTER TABLE catering_packages ADD COLUMN IF NOT EXISTS ingredient_total_cost FLOAT DEFAULT 0.0;"
    ]
    
    print("Starting database migration for internal costing fields...")
    try:
        with engine.connect() as conn:
            for cmd in commands:
                print(f"Executing: {cmd}")
                conn.execute(text(cmd))
                conn.commit()
            print("Migration successful! Added internal costing columns to catering_packages.")
    except Exception as e:
        print(f"Error during migration: {str(e)}")

if __name__ == "__main__":
    upgrade()
