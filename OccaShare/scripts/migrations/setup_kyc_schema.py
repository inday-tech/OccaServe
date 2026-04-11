from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Starting KYC Schema Migration...")

        # 1. Update users table
        print("Updating 'users' table...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_kyc_complete BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_attempts INTEGER DEFAULT 0;"))
            conn.commit()
            print("Successfully updated 'users'.")
        except Exception as e:
            print(f"Error updating 'users': {e}")
            conn.rollback()

        # 2. Update bookings table
        print("Updating 'bookings' table...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS ocr_verified BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE bookings ADD COLUMN IF NOT EXISTS liveness_verified BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully updated 'bookings'.")
        except Exception as e:
            print(f"Error updating 'bookings': {e}")
            conn.rollback()

        # 3. Create identity_verifications
        print("Creating 'identity_verifications' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS identity_verifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER UNIQUE REFERENCES users(id),
                    verification_type VARCHAR DEFAULT 'government_id',
                    document_url VARCHAR NOT NULL,
                    id_number VARCHAR,
                    selfie_url VARCHAR NOT NULL,
                    selfie_2_url VARCHAR,
                    selfie_3_url VARCHAR,
                    ocr_data JSONB,
                    verification_status VARCHAR DEFAULT 'pending',
                    failure_reason TEXT,
                    fraud_score INTEGER DEFAULT 0,
                    ip_address VARCHAR,
                    device_info JSONB,
                    liveness_status VARCHAR,
                    verified_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
            print("Successfully created 'identity_verifications'.")
        except Exception as e:
            print(f"Error creating 'identity_verifications': {e}")
            conn.rollback()

        # 4. Create refresh_tokens
        print("Creating 'refresh_tokens' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    token VARCHAR UNIQUE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    is_revoked BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token ON refresh_tokens (token);
            """))
            conn.commit()
            print("Successfully created 'refresh_tokens'.")
        except Exception as e:
            print(f"Error creating 'refresh_tokens': {e}")
            conn.rollback()

        # 5. Create audit_logs
        print("Creating 'audit_logs' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    action VARCHAR,
                    old_status VARCHAR,
                    new_status VARCHAR,
                    ip_address VARCHAR,
                    device_info JSONB,
                    notes TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
            print("Successfully created 'audit_logs'.")
        except Exception as e:
            print(f"Error creating 'audit_logs': {e}")
            conn.rollback()

        # 6. Create verification_attempts
        print("Creating 'verification_attempts' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS verification_attempts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    booking_id INTEGER REFERENCES bookings(id),
                    step VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    details JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
            print("Successfully created 'verification_attempts'.")
        except Exception as e:
            print(f"Error creating 'verification_attempts': {e}")
            conn.rollback()

        # 7. Create fraud_flags
        print("Creating 'fraud_flags' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fraud_flags (
                    id SERIAL PRIMARY KEY,
                    booking_id INTEGER REFERENCES bookings(id),
                    flag_type VARCHAR(50),
                    description TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            conn.commit()
            print("Successfully created 'fraud_flags'.")
        except Exception as e:
            print(f"Error creating 'fraud_flags': {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
