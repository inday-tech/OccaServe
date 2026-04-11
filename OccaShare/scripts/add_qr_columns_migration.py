from sqlalchemy import create_engine, text
import sys
import os

# Add the project root to sys.path so we can import app
sys.path.append(os.getcwd())

from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Checking for existing columns in 'caterer_profiles'...")
        
        # Adding maya_qr_url
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN maya_qr_url VARCHAR;"))
            conn.commit()
            print("Successfully added 'maya_qr_url'.")
        except Exception as e:
            print(f"Error adding 'maya_qr_url' (it might already exist): {e}")
            conn.rollback()

        # Adding bank_qr_url
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN bank_qr_url VARCHAR;"))
            conn.commit()
            print("Successfully added 'bank_qr_url'.")
        except Exception as e:
            print(f"Error adding 'bank_qr_url' (it might already exist): {e}")
            conn.rollback()

    print("Migration complete!")

if __name__ == "__main__":
    migrate()

if __name__ == "__main__":
    migrate()
