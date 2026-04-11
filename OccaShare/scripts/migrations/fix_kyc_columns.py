from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Starting KYC Schema Hardening Migration...")

        # Columns to add to identity_verifications
        id_verify_cols = [
            ("id_number", "VARCHAR"),
            ("selfie_2_url", "VARCHAR"),
            ("selfie_3_url", "VARCHAR"),
            ("fraud_score", "INTEGER DEFAULT 0"),
            ("ip_address", "VARCHAR"),
            ("device_info", "JSONB"),
            ("liveness_status", "VARCHAR")
        ]

        for col_name, col_type in id_verify_cols:
            print(f"Checking {col_name} in identity_verifications...")
            try:
                conn.execute(text(f"ALTER TABLE identity_verifications ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                conn.commit()
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
                conn.rollback()

        # Check users table again just in case
        user_cols = [
            ("is_kyc_complete", "BOOLEAN DEFAULT FALSE"),
            ("kyc_attempts", "INTEGER DEFAULT 0")
        ]
        for col_name, col_type in user_cols:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                conn.commit()
            except Exception as e:
                conn.rollback()

        # Check bookings table
        booking_cols = [
            ("ocr_verified", "BOOLEAN DEFAULT FALSE"),
            ("liveness_verified", "BOOLEAN DEFAULT FALSE")
        ]
        for col_name, col_type in booking_cols:
            try:
                conn.execute(text(f"ALTER TABLE bookings ADD COLUMN IF NOT EXISTS {col_name} {col_type};"))
                conn.commit()
            except Exception as e:
                conn.rollback()

        print("Migration complete.")

if __name__ == "__main__":
    migrate()
