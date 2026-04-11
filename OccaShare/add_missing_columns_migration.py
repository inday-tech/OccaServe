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
    pwd = os.getenv("DB_PASSWORD", "1425")
    port_id = os.getenv("DB_PORT", "5432")
    DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

def migrate():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        print("Starting migration: Adding missing columns...")
        
        # Format: (table_name, column_name, column_definition)
        migrations = [
            # catering_packages
            ('catering_packages', 'cost_price', 'FLOAT DEFAULT 0.0'),
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
            ('menu_items', 'dietary_tags', 'VARCHAR[] NULL'),
            ('menu_items', 'allergen_info', 'VARCHAR[] NULL'),
            ('menu_items', 'serving_size', 'VARCHAR NULL'),
            ('menu_items', 'is_addon', 'BOOLEAN DEFAULT FALSE'),
            ('menu_items', 'addon_price', 'FLOAT DEFAULT 0.0'),
            ('menu_items', 'is_hidden', 'BOOLEAN DEFAULT FALSE'),
            ('menu_items', 'is_archived', 'BOOLEAN DEFAULT FALSE'),
            
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
        
        for table, column, definition in migrations:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")
                print(f"✅ Added {column} to {table}")
            except psycopg2.errors.DuplicateColumn:
                conn.rollback()
                print(f"ℹ️ Column {column} already exists in {table}")
            except Exception as e:
                conn.rollback()
                print(f"❌ Error adding {column} to {table}: {e}")
            else:
                conn.commit()
                
        cur.close()
        conn.close()
        print("\nMigration complete.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    migrate()
