from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Relaxing NOT NULL constraint on 'selfie_url' in 'identity_verifications'...")
        try:
            # Drop NOT NULL constraint on selfie_url
            conn.execute(text("ALTER TABLE identity_verifications ALTER COLUMN selfie_url DROP NOT NULL;"))
            conn.commit()
            print("Successfully updated 'identity_verifications'.")
        except Exception as e:
            print(f"Error updating 'identity_verifications': {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
