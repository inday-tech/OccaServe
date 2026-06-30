from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN out_of_coverage_action VARCHAR DEFAULT 'reject';"))
        conn.commit()
        print("Successfully added out_of_coverage_action column.")
    except Exception as e:
        print("Error adding column:", e)
