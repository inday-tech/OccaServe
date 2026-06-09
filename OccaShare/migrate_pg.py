from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN permit_status VARCHAR DEFAULT 'Pending'"))
        conn.commit()
        print("Column permit_status added successfully.")
    except Exception as e:
        print("Error:", e)
