import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from app.db.database import engine
from sqlalchemy import text

def migrate():
    new_columns = [
        ("sidebar_decoration", "VARCHAR"),
        ("header_decoration", "VARCHAR")
    ]
    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            try:
                check_query = text(f"SELECT column_name FROM information_schema.columns WHERE table_name='caterer_profiles' AND column_name='{col_name}';")
                if not conn.execute(check_query).fetchone():
                    conn.execute(text(f"ALTER TABLE caterer_profiles ADD COLUMN {col_name} {col_type} DEFAULT 'none';"))
                    conn.commit()
                    print(f"Added {col_name}")
            except Exception as e:
                print(f"Error {col_name}: {e}")

if __name__ == "__main__":
    migrate()
