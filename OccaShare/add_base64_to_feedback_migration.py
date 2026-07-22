import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE platform_feedback ADD COLUMN attachment_base64 TEXT"))
            print("Successfully added attachment_base64 to platform_feedback")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("Column attachment_base64 already exists in platform_feedback")
        else:
            print(f"Error altering table platform_feedback: {e}")

if __name__ == "__main__":
    migrate()
