import sys
import os
sys.path.append(os.path.abspath('C:/OccaServe/OccaShare'))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    columns_to_add = [
        ("capacity_type", "VARCHAR DEFAULT 'unit_based'"),
        ("staff_to_pax_ratio", "INTEGER DEFAULT 0"),
        ("min_staff_required", "INTEGER DEFAULT 1"),
        ("allow_freelancers", "BOOLEAN DEFAULT false"),
        ("buffer_time_hours", "INTEGER DEFAULT 0")
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE services ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Added column {col_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    print(f"Column {col_name} already exists.")
                else:
                    print(f"Error adding {col_name}: {e}")
                    conn.rollback()

if __name__ == '__main__':
    migrate()
