import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.db.database import engine
from sqlalchemy import text

def add_json_columns():
    with engine.connect() as conn:
        print("Connected to DB.")
        try:
            conn.execute(text('ALTER TABLE equipment ADD COLUMN details_json JSONB;'))
            print("Added details_json to equipment.")
        except Exception as e:
            print("Equipment table already has details_json or error:", e)
            
        try:
            conn.execute(text('ALTER TABLE services ADD COLUMN details_json JSONB;'))
            print("Added details_json to services.")
        except Exception as e:
            print("Services table already has details_json or error:", e)
        
        conn.commit()
    print("Migration complete.")

if __name__ == '__main__':
    add_json_columns()
