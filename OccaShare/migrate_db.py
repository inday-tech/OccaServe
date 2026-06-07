import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db.database import engine
from sqlalchemy import text

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE bookings ADD COLUMN customer_archived BOOLEAN DEFAULT FALSE;"))
    print("Column added successfully!")
except Exception as e:
    print(f"Error (maybe already exists): {e}")
