import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Primary connection string
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to local development components
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def migrate():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Starting migration: Adding missing columns to 'users' table...")
        
        # Format: (column_name, column_definition)
        migrations = [
            ('middle_name', 'VARCHAR(255) NULL'),
            ('dob', 'DATE NULL'),
            ('facebook_id', 'VARCHAR(255) UNIQUE NULL'),
            ('google_id', 'VARCHAR(255) UNIQUE NULL'),
            ('instagram_id', 'VARCHAR(255) UNIQUE NULL'),
            ('auth_provider', "VARCHAR(50) DEFAULT 'email'"),
            ('is_email_verified', 'BOOLEAN DEFAULT FALSE'),
            ('verification_code', 'VARCHAR(20) NULL'),
            ('otp_expires_at', 'TIMESTAMP WITH TIME ZONE NULL'),
            ('is_kyc_complete', 'BOOLEAN DEFAULT FALSE'),
            ('kyc_attempts', 'INTEGER DEFAULT 0'),
            ('must_change_password', 'BOOLEAN DEFAULT FALSE'),
            ('is_archived', 'BOOLEAN DEFAULT FALSE')
        ]

        
        for column, definition in migrations:
            try:
                cur.execute(f"ALTER TABLE users ADD COLUMN {column} {definition};")
                print(f"[OK] Added {column} to users")
            except psycopg2.errors.DuplicateColumn:
                conn.rollback()
                print(f"[SKIP] Column {column} already exists in users")
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Error adding {column} to users: {e}")
            else:
                conn.commit()

                
        cur.close()
        conn.close()
        print("\nMigration complete.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    migrate()
