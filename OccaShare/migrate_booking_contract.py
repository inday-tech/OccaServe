from sqlalchemy import text
from app.db.database import engine

def migrate():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE booking_contracts ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE;"))
        conn.commit()
    print("Migration successful")

if __name__ == "__main__":
    migrate()
