import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Primary connection string construction
hostname = os.getenv("DB_HOST", "localhost")
database = os.getenv("DB_NAME", "occashare")
username = os.getenv("DB_USER", "postgres")
pwd = os.getenv("DB_PASSWORD", "1425")
port_id = os.getenv("DB_PORT", "5432")
DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def migrate():
    try:
        print(f"Connecting to database: {database} as {username}...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("\n🚀 Starting Dynamic Migration: Adding missing columns from Diamond update...\n")
        
        # Format: (table_name, column_name, column_definition)
        migrations = [
            # catering_packages
            ('catering_packages', 'cost_price', 'FLOAT DEFAULT 0.0'),
            ('catering_packages', 'cost_breakdown', 'JSONB NULL'),
            ('catering_packages', 'price_per_head', 'FLOAT NULL'),
            ('catering_packages', 'min_contract_amount', 'FLOAT NULL'),
            ('catering_packages', 'additional_guest_price', 'FLOAT NULL'),
            ('catering_packages', 'service_duration', 'INTEGER DEFAULT 4'),
            ('catering_packages', 'overtime_fee', 'FLOAT DEFAULT 0.0'),
            ('catering_packages', 'location_coverage', 'VARCHAR NULL'),
            ('catering_packages', 'inclusions', 'JSONB NULL'),
            ('catering_packages', 'policies', 'JSONB NULL'),
            ('catering_packages', 'status', "VARCHAR DEFAULT 'active'"),
            
            # menu_items
            ('menu_items', 'cost_price', 'FLOAT DEFAULT 0.0'),
            ('menu_items', 'cost_breakdown', 'JSONB NULL'),
            ('menu_items', 'dietary_tags', 'VARCHAR[] NULL'),
            ('menu_items', 'allergen_info', 'VARCHAR[] NULL'),
            ('menu_items', 'serving_size', 'VARCHAR NULL'),
            ('menu_items', 'is_addon', 'BOOLEAN DEFAULT FALSE'),
            ('menu_items', 'addon_price', 'FLOAT DEFAULT 0.0'),
            ('menu_items', 'is_hidden', 'BOOLEAN DEFAULT FALSE'),
            ('menu_items', 'is_archived', 'BOOLEAN DEFAULT FALSE'),
            
            # bookings
            ('bookings', 'actual_cost', 'FLOAT DEFAULT 0.0'),
            ('bookings', 'actual_cost_breakdown', 'JSONB NULL'),
            ('bookings', 'total_price', 'FLOAT NULL'),
            ('bookings', 'balance_due_date', 'TIMESTAMP WITH TIME ZONE NULL'),
            ('bookings', 'event_location', 'TEXT NULL'),
            ('bookings', 'payment_verification_data', 'JSONB NULL'),
            ('bookings', 'proof_image_hash', 'VARCHAR NULL'),
            ('bookings', 'ocr_verified', 'BOOLEAN DEFAULT FALSE'),
            ('bookings', 'liveness_verified', 'BOOLEAN DEFAULT FALSE'),

            # users
            ('users', 'is_archived', 'BOOLEAN DEFAULT FALSE'),
            ('users', 'is_kyc_complete', 'BOOLEAN DEFAULT FALSE'),
            ('users', 'kyc_attempts', 'INTEGER DEFAULT 0'),
            ('users', 'must_change_password', 'BOOLEAN DEFAULT FALSE'),

            # caterer_profiles
            ('caterer_profiles', 'min_pax', 'INTEGER DEFAULT 0'),
            ('caterer_profiles', 'starting_price', 'FLOAT DEFAULT 0.0'),
            ('caterer_profiles', 'sample_menu_url', 'VARCHAR NULL'),
            ('caterer_profiles', 'permit_url', 'VARCHAR NULL'),
            ('caterer_profiles', 'gov_id_url', 'VARCHAR NULL'),
            ('caterer_profiles', 'primary_color', "VARCHAR DEFAULT '#2D3748'"),
            ('caterer_profiles', 'secondary_color', "VARCHAR DEFAULT '#4A5568'"),
            ('caterer_profiles', 'accent_color', "VARCHAR DEFAULT '#48BB78'"),
            ('caterer_profiles', 'highlight_color', "VARCHAR DEFAULT '#48BB78'"),
            ('caterer_profiles', 'font_family', "VARCHAR DEFAULT 'Inter'"),
            ('caterer_profiles', 'border_radius', 'INTEGER DEFAULT 12'),
            ('caterer_profiles', 'sidebar_mode', "VARCHAR DEFAULT 'full'"),
            ('caterer_profiles', 'show_platform_logo', 'BOOLEAN DEFAULT TRUE'),
            ('caterer_profiles', 'booking_policy', 'TEXT NULL'),
            ('caterer_profiles', 'payment_policy', 'TEXT NULL'),
            ('caterer_profiles', 'cancellation_policy', 'TEXT NULL')
        ]
        
        success_count = 0
        skip_count = 0
        
        for table, column, definition in migrations:
            try:
                # Check if column exists first
                cur.execute(f"""
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name='{table}' AND column_name='{column}';
                """)
                exists = cur.fetchone()
                
                if not exists:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")
                    print(f"✅ Added '{column}' to '{table}'")
                    success_count += 1
                else:
                    print(f"ℹ️ Column '{column}' already exists in '{table}'")
                    skip_count += 1
            except Exception as e:
                conn.rollback()
                print(f"❌ Error adding '{column}' to '{table}': {e}")
            else:
                conn.commit()
                
        cur.close()
        conn.close()
        print(f"\n✨ Migration Finished! Loaded: {success_count}, Skipped: {skip_count}")
        print("You can now restart your FastAPI server.")
        
    except Exception as e:
        print(f"Critical connection error: {e}")

if __name__ == "__main__":
    migrate()
