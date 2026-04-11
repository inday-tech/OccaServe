from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding 'balance_due_date' column to 'bookings'...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN balance_due_date TIMESTAMP WITH TIME ZONE;"))
            conn.commit()
            print("Successfully added 'balance_due_date'.")
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
