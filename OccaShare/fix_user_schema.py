from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")

    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        print("Checking for missing columns in 'users' table...")
        
        columns_to_add = [
            ("address", "TEXT"),
            ("facebook_id", "VARCHAR UNIQUE"),
            ("google_id", "VARCHAR UNIQUE"),
            ("instagram_id", "VARCHAR UNIQUE"),
            ("auth_provider", "VARCHAR DEFAULT 'email'"),
            ("is_email_verified", "BOOLEAN DEFAULT FALSE"),
            ("verification_code", "VARCHAR"),
            ("otp_expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("reset_token", "VARCHAR UNIQUE"),
            ("reset_token_expires", "TIMESTAMP WITH TIME ZONE"),
            ("is_kyc_complete", "BOOLEAN DEFAULT FALSE"),
            ("kyc_attempts", "INTEGER DEFAULT 0"),
            ("profile_image_url", "VARCHAR"),
            ("status", "VARCHAR DEFAULT 'active'"),
            ("is_verified", "BOOLEAN DEFAULT FALSE"),
            ("last_login", "TIMESTAMP WITH TIME ZONE"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE"),
        ]

        for col_name, col_type in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Successfully added '{col_name}' column.")
            except Exception as e:
                # Catching duplicate column error
                if "already exists" in str(e):
                    print(f"Note: '{col_name}' column already exists.")
                else:
                    print(f"Error adding '{col_name}': {e}")
                conn.rollback()

if __name__ == "__main__":
    migrate()
