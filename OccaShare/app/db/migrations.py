from sqlalchemy import text
from .database import engine

def ensure_columns():
    with engine.connect() as conn:
        # 1. Check/Add columns for 'users' table
        users_columns = [
            ("must_change_password", "BOOLEAN DEFAULT FALSE"),
            ("security_flag", "BOOLEAN DEFAULT FALSE"),
            ("is_kyc_complete", "BOOLEAN DEFAULT FALSE"),
            ("kyc_attempts", "INTEGER DEFAULT 0"),
            ("is_email_verified", "BOOLEAN DEFAULT FALSE"),
            ("verification_code", "VARCHAR"),
            ("otp_expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("reset_token", "VARCHAR UNIQUE"),
            ("reset_token_expires", "TIMESTAMP WITH TIME ZONE"),
            ("status", "VARCHAR DEFAULT 'active'"),
            ("is_verified", "BOOLEAN DEFAULT FALSE"),
            ("last_login", "TIMESTAMP WITH TIME ZONE"),
            ("address", "TEXT"),
            ("profile_image_url", "VARCHAR"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE"),
        ]

        for col_name, col_type in users_columns:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Migration: Added '{col_name}' to 'users'.")
            except Exception as e:
                # Silently skip if it already exists
                if "already exists" not in str(e).lower():
                    print(f"Migration Error on 'users.{col_name}': {e}")
                conn.rollback()

        # 2. Check/Add columns for 'identity_verifications' table
        id_ver_columns = [
            ("id_expiry_date", "DATE"),
            ("verified_at", "TIMESTAMP WITH TIME ZONE"),
        ]

        for col_name, col_type in id_ver_columns:
            try:
                conn.execute(text(f"ALTER TABLE identity_verifications ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Migration: Added '{col_name}' to 'identity_verifications'.")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"Migration Error on 'identity_verifications.{col_name}': {e}")
                conn.rollback()
