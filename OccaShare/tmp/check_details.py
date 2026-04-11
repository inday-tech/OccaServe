import sys
import os
from sqlalchemy import create_engine, text

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.db.database import SQLALCHEMY_DATABASE_URL

def check_db_details():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as connection:
        query = text("SELECT current_database(), current_user, version();")
        result = connection.execute(query).fetchone()
        print(f"Database: {result[0]}")
        print(f"User: {result[1]}")
        print(f"Version: {result[2]}")

if __name__ == "__main__":
    check_db_details()
