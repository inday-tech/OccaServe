import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.db.database import engine
from sqlalchemy import text

def check_db():
    try:
        with engine.connect() as conn:
            print(f"Connected to: {engine.url}")
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users';"))
            columns = [row[0] for row in result]
            print(f"Columns in 'users': {columns}")
            
            if 'middle_initial' in columns:
                print("middle_initial FOUND.")
            else:
                print("middle_initial MISSING.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
