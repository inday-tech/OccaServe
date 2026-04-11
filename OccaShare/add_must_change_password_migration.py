
from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding 'must_change_password' column to 'users' table...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added 'must_change_password'.")
        except Exception as e:
            print(f"Error adding 'must_change_password': {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
