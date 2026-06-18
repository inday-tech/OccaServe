import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)

# Primary connection string
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    hostname = os.getenv("DB_HOST", "localhost")
    database = os.getenv("DB_NAME", "occashare")
    username = os.getenv("DB_USER", "postgres")
    pwd = os.getenv("DB_PASSWORD", "2004")
    port_id = os.getenv("DB_PORT", "5432")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{username}:{pwd}@{hostname}:{port_id}/{database}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def run_migration():
    with engine.begin() as conn:
        print("Starting Phase 1 Database Migration...")
        
        # 1. Add missing columns to menu_items
        try:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN min_order_qty INTEGER DEFAULT 1;"))
            print("Added min_order_qty to menu_items")
        except Exception as e:
            print("min_order_qty might already exist:", e)

        try:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN status VARCHAR DEFAULT 'available';"))
            print("Added status to menu_items")
        except Exception as e:
            print("status might already exist:", e)

        # 2. Rename PackageItem to PackageMenu (table rename)
        try:
            conn.execute(text("ALTER TABLE package_items RENAME TO package_menus;"))
            print("Renamed package_items to package_menus")
        except Exception as e:
            print("package_menus might already exist:", e)

        # 3. Create equipment table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS equipment (
                    id SERIAL PRIMARY KEY,
                    caterer_id INTEGER REFERENCES caterer_profiles(id),
                    name VARCHAR,
                    category VARCHAR,
                    description TEXT,
                    image_url VARCHAR,
                    available_qty INTEGER DEFAULT 1,
                    cost_value FLOAT DEFAULT 0.0,
                    rental_price FLOAT DEFAULT 0.0,
                    unit_type VARCHAR DEFAULT 'piece',
                    status VARCHAR DEFAULT 'available',
                    is_archived BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("Created equipment table")
        except Exception as e:
            print("Error creating equipment table:", e)

        # 4. Create services table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS services (
                    id SERIAL PRIMARY KEY,
                    caterer_id INTEGER REFERENCES caterer_profiles(id),
                    name VARCHAR,
                    description TEXT,
                    cost FLOAT DEFAULT 0.0,
                    selling_price FLOAT DEFAULT 0.0,
                    unit_type VARCHAR DEFAULT 'per_event',
                    max_available INTEGER DEFAULT 1,
                    status VARCHAR DEFAULT 'available',
                    is_archived BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("Created services table")
        except Exception as e:
            print("Error creating services table:", e)

        # 5. Create package_equipment table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS package_equipment (
                    id SERIAL PRIMARY KEY,
                    package_id INTEGER REFERENCES catering_packages(id) ON DELETE CASCADE,
                    equipment_id INTEGER REFERENCES equipment(id) ON DELETE CASCADE,
                    quantity INTEGER DEFAULT 1
                );
            """))
            print("Created package_equipment table")
        except Exception as e:
            print("Error creating package_equipment table:", e)

        # 6. Drop old unused tables if they exist
        try:
            conn.execute(text("DROP TABLE IF EXISTS menu_item_ingredients CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS ingredients CASCADE;"))
            print("Dropped old ingredient tables")
        except Exception as e:
            print("Error dropping ingredient tables:", e)
            
        print("Phase 1 Database Migration Complete!")

if __name__ == "__main__":
    run_migration()
