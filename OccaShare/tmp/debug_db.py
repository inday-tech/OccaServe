import sys
import os
from sqlalchemy import create_engine, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.db.database import SQLALCHEMY_DATABASE_URL

def debug_columns():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        query = text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='reviews'
            ORDER BY ordinal_position;
        """)
        results = connection.execute(query).fetchall()
        print("Columns in 'reviews' table:")
        for row in results:
            print(f"- {row[0]} ({row[1]})")

if __name__ == "__main__":
    debug_columns()
