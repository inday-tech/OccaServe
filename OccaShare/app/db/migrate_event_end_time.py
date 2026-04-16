from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def upgrade():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN event_end_time TIME"))
            print("Successfully added event_end_time column to bookings")
        except Exception as e:
            print("Migration failed or column already exists:", e)
        conn.commit()

if __name__ == "__main__":
    upgrade()
