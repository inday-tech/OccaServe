from sqlalchemy import create_engine, text
from app.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # We use a separate connection for each attempt to ensure one failure doesn't block the rest
    def try_add_column(sql):
        with engine.connect() as conn:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Executed: {sql}")
            except Exception as e:
                print(f"Skipped/Error for '{sql}': {e}")

    print("Starting robust migration...")
    try_add_column("ALTER TABLE bookings ADD COLUMN payment_method VARCHAR;")
    try_add_column("ALTER TABLE bookings ADD COLUMN ocr_verified BOOLEAN DEFAULT FALSE;")
    try_add_column("ALTER TABLE bookings ADD COLUMN liveness_verified BOOLEAN DEFAULT FALSE;")
    print("Migration finished!")

if __name__ == "__main__":
    migrate()
