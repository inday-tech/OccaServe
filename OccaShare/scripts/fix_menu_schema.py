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
        print("Creating 'package_items' table if not exists...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS package_items (
                    package_id INTEGER REFERENCES catering_packages(id) ON DELETE CASCADE,
                    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
                    PRIMARY KEY (package_id, menu_item_id)
                );
            """))
            conn.commit()
            print("Successfully checked/created 'package_items' table.")
        except Exception as e:
            print(f"Error creating 'package_items' table: {e}")
            conn.rollback()

        print("Checking for missing columns in 'menu_items' table...")
        menu_items_columns = [
            ("caterer_id", "INTEGER REFERENCES caterer_profiles(id)"),
            ("dietary_tags", "VARCHAR[]"),
            ("allergen_info", "VARCHAR[]"),
            ("serving_size", "VARCHAR"),
            ("is_addon", "BOOLEAN DEFAULT FALSE"),
            ("addon_price", "FLOAT DEFAULT 0.0"),
            ("image_url", "VARCHAR"),
            ("is_hidden", "BOOLEAN DEFAULT FALSE"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
        ]

        for col_name, col_type in menu_items_columns:
            try:
                conn.execute(text(f"ALTER TABLE menu_items ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Successfully added '{col_name}' to 'menu_items'.")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"Note: '{col_name}' column already exists in 'menu_items'.")
                else:
                    print(f"Error adding '{col_name}' to 'menu_items': {e}")
                conn.rollback()

        print("Checking for missing columns in 'catering_packages' table...")
        package_columns = [
            ("price_per_head", "FLOAT"),
            ("min_contract_amount", "FLOAT"),
            ("additional_guest_price", "FLOAT"),
            ("service_duration", "INTEGER DEFAULT 4"),
            ("overtime_fee", "FLOAT DEFAULT 0.0"),
            ("location_coverage", "VARCHAR"),
            ("inclusions", "JSONB"),
            ("policies", "JSONB"),
        ]

        for col_name, col_type in package_columns:
            try:
                conn.execute(text(f"ALTER TABLE catering_packages ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Successfully added '{col_name}' to 'catering_packages'.")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"Note: '{col_name}' column already exists in 'catering_packages'.")
                else:
                    print(f"Error adding '{col_name}' to 'catering_packages': {e}")
                conn.rollback()

        # Data Migration: If menu_items has an old package_id column, migrate it to package_items
        try:
            print("Checking if data migration from menu_items.package_id is needed...")
            # Check if package_id column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='menu_items' AND column_name='package_id';"))
            if result.fetchone():
                print("Found 'package_id' in 'menu_items'. Migrating to 'package_items' table...")
                conn.execute(text("INSERT INTO package_items (package_id, menu_item_id) SELECT package_id, id FROM menu_items WHERE package_id IS NOT NULL ON CONFLICT DO NOTHING;"))
                print("Data migration successful.")
                # We don't drop the column yet to be safe, but the app will use the new table
            else:
                print("No 'package_id' column in 'menu_items', skipping data migration.")
            conn.commit()
        except Exception as e:
            print(f"Error during data migration: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
