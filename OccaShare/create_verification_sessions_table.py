import sys
import os

# Add root directory to path
sys.path.append(os.getcwd())

from app.db.database import engine
from app.db.models import Base

def create_table():
    try:
        print("Synchronizing database metadata and creating missing tables...")
        Base.metadata.create_all(bind=engine)
        print("Successfully synchronized tables!")
    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_table()
