from sqlalchemy import text
from app.db.database import SessionLocal

def add_upgrade_fee_column():
    session = SessionLocal()
    try:
        # Check if column exists
        result = session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='menu_items' AND column_name='upgrade_fee'"))
        if not result.fetchone():
            print("Adding upgrade_fee column to menu_items...")
            session.execute(text("ALTER TABLE menu_items ADD COLUMN upgrade_fee DOUBLE PRECISION DEFAULT 0.0"))
            session.commit()
            print("Column added successfully.")
        else:
            print("Column upgrade_fee already exists.")
    except Exception as e:
        print(f"Migration Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_upgrade_fee_column()
