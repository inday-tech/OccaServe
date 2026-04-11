from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        print("Adding payment proof columns to bookings table...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN payment_reference VARCHAR"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN payment_proof_url VARCHAR"))
            conn.commit()
            print("Successfully added columns.")
        except Exception as e:
            print(f"Error adding columns: {e}")

if __name__ == "__main__":
    migrate()
