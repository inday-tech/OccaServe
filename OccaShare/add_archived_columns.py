import sys
import os
from sqlalchemy import create_engine, text

# Get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

try:
    from app.db.database import SQLALCHEMY_DATABASE_URL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
except ImportError:
    print("Error: Could not import app.db.database. Ensure you are running this from the project root.")
    sys.exit(1)

def migrate():
    with engine.connect() as conn:
        print("Starting comprehensive database synchronization...")
        
        # List of (table_name, column_name, column_type)
        migrations = [
            ("users", "is_archived", "BOOLEAN DEFAULT FALSE"),
            ("bookings", "is_archived", "BOOLEAN DEFAULT FALSE"),
            ("reviews", "is_archived", "BOOLEAN DEFAULT FALSE"),
            ("payouts", "is_archived", "BOOLEAN DEFAULT FALSE"),
            ("identity_verifications", "is_archived", "BOOLEAN DEFAULT FALSE"),
            ("caterer_gallery", "is_archived", "BOOLEAN DEFAULT FALSE"),
            ("menu_items", "is_archived", "BOOLEAN DEFAULT FALSE"),
            ("identity_verifications", "fraud_score", "INTEGER DEFAULT 0"),
            ("identity_verifications", "ip_address", "VARCHAR"),
            ("identity_verifications", "device_info", "JSONB"),
            ("identity_verifications", "liveness_status", "VARCHAR"),
            ("identity_verifications", "verified_at", "TIMESTAMP WITH TIME ZONE"),
            ("identity_verifications", "selfie_2_url", "VARCHAR"),
            ("identity_verifications", "selfie_3_url", "VARCHAR"),
            ("identity_verifications", "ocr_data", "JSONB")
        ]
        
        for table_name, col_name, col_type in migrations:
            print(f"Checking '{col_name}' in '{table_name}'...")
            try:
                # Optimized check for PostgreSQL
                check_query = text(f"""
                    SELECT count(*) 
                    FROM information_schema.columns 
                    WHERE table_name='{table_name}' AND column_name='{col_name}';
                """)
                exists = conn.execute(check_query).scalar()
                
                if not exists:
                    print(f"Adding '{col_name}' to '{table_name}'...")
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};"))
                    conn.commit()
                    print(f"Successfully added '{col_name}'.")
                else:
                    print(f"Column '{col_name}' already exists in '{table_name}'. Skipping.")
            except Exception as e:
                print(f"Error processing '{col_name}' in '{table_name}': {e}")
                conn.rollback()

        print("Migration complete!")

if __name__ == "__main__":
    migrate()
