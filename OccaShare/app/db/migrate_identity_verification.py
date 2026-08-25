import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'occashare.db')

def migrate_identity_verification():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting Identity Verification migration...")
    
    # 1. Remove unique constraint from user_id in identity_verifications
    # SQLite doesn't support DROP CONSTRAINT, so we typically have to recreate the table,
    # but since this is just an index in SQLite, we might just leave it if it's not strictly enforced by a UNIQUE index,
    # OR we recreate the table to be safe.
    
    cursor.execute("PRAGMA foreign_keys=off;")
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='identity_verifications'")
    if not cursor.fetchone():
        print("Table identity_verifications does not exist. Nothing to migrate.")
        return

    # Create new table with updated schema
    cursor.execute("""
        CREATE TABLE identity_verifications_new (
            id INTEGER NOT NULL PRIMARY KEY,
            user_id INTEGER,
            booking_id INTEGER,
            verification_type VARCHAR,
            document_url VARCHAR,
            document_back_url VARCHAR,
            id_type VARCHAR,
            id_number VARCHAR,
            id_expiry_date DATE,
            selfie_url VARCHAR,
            selfie_2_url VARCHAR,
            selfie_3_url VARCHAR,
            ocr_data JSON,
            ocr_status VARCHAR,
            liveness_status VARCHAR,
            match_status VARCHAR,
            verification_status VARCHAR DEFAULT 'PROCESSING',
            failure_reason TEXT,
            verified_at DATETIME,
            verification_valid_until DATETIME,
            review_status VARCHAR,
            reviewed_by INTEGER,
            reviewed_at DATETIME,
            is_archived BOOLEAN DEFAULT 0,
            fraud_score INTEGER DEFAULT 0,
            match_score FLOAT DEFAULT 0.0,
            face_detected BOOLEAN DEFAULT 0,
            id_detected BOOLEAN DEFAULT 0,
            ip_address VARCHAR,
            device_info JSON,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users (id),
            FOREIGN KEY(booking_id) REFERENCES bookings (id),
            FOREIGN KEY(reviewed_by) REFERENCES users (id)
        )
    """)

    # Copy data
    print("Copying existing data...")
    # Map old columns to new columns
    cursor.execute("""
        INSERT INTO identity_verifications_new (
            id, user_id, verification_type, document_url, document_back_url, 
            id_number, selfie_url, selfie_2_url, selfie_3_url, ocr_data, 
            verification_status, failure_reason, is_archived, fraud_score, 
            match_score, face_detected, id_detected, ip_address, device_info, 
            liveness_status, verified_at, created_at
        )
        SELECT 
            id, user_id, verification_type, document_url, document_back_url, 
            id_number, selfie_url, selfie_2_url, selfie_3_url, ocr_data, 
            verification_status, failure_reason, is_archived, fraud_score, 
            match_score, face_detected, id_detected, ip_address, device_info, 
            liveness_status, verified_at, created_at
        FROM identity_verifications
    """)

    # Drop old table
    cursor.execute("DROP TABLE identity_verifications")

    # Rename new table
    cursor.execute("ALTER TABLE identity_verifications_new RENAME TO identity_verifications")
    
    # Create indices
    cursor.execute("CREATE INDEX ix_identity_verifications_id ON identity_verifications (id)")
    # NO UNIQUE INDEX on user_id anymore, but we can add regular index
    cursor.execute("CREATE INDEX ix_identity_verifications_user_id ON identity_verifications (user_id)")
    
    conn.commit()
    cursor.execute("PRAGMA foreign_keys=on;")
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_identity_verification()
