
from app.db.database import engine
from sqlalchemy import text

def update_db():
    cols = [
        ("match_score", "FLOAT DEFAULT 0.0"),
        ("face_detected", "BOOLEAN DEFAULT FALSE"),
        ("id_detected", "BOOLEAN DEFAULT FALSE")
    ]
    
    with engine.connect() as conn:
        for col_name, col_type in cols:
            try:
                print(f"Adding column {col_name} to identity_verifications...")
                conn.execute(text(f"ALTER TABLE identity_verifications ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"Column {col_name} added successfully.")
            except Exception as e:
                print(f"Could not add {col_name} (it might already exist): {e}")
                conn.rollback()

if __name__ == "__main__":
    update_db()
