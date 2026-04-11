import sys
import os
from sqlalchemy import create_engine, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.db.database import SQLALCHEMY_DATABASE_URL

def find_reviews_tables():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        query = text("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name='reviews';
        """)
        results = connection.execute(query).fetchall()
        print("Tables found:")
        for row in results:
            print(f"- Schema: {row[0]}, Table: {row[1]}")
            
        # Also check columns per schema
        query2 = text("""
            SELECT table_schema, column_name 
            FROM information_schema.columns 
            WHERE table_name='reviews' AND column_name='is_highlighted';
        """)
        results2 = connection.execute(query2).fetchall()
        print("\nColumns found:")
        for row in results2:
            print(f"- Schema: {row[0]}, Column: {row[1]}")

if __name__ == "__main__":
    find_reviews_tables()
