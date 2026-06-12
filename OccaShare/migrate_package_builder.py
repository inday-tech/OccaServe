import psycopg2
import os
import traceback
from dotenv import load_dotenv

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
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
        
        print("Starting migration: Adding missing columns for Package Builder...")
        
        migrations = [
            ('catering_packages', 'pricing_mode', "VARCHAR DEFAULT 'per_pax'"),
            ('catering_packages', 'transportation_cost', 'FLOAT DEFAULT 0.0'),
            ('catering_packages', 'miscellaneous_cost', 'FLOAT DEFAULT 0.0'),
            ('catering_packages', 'reservation_fee_type', "VARCHAR DEFAULT 'fixed'"),
            ('catering_packages', 'reservation_fee_value', 'FLOAT DEFAULT 0.0'),
        ]
        
        for table, column, definition in migrations:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")
                print(f"[OK] Added {column} to {table}")
            except psycopg2.errors.DuplicateColumn:
                conn.rollback()
                print(f"[SKIP] Column {column} already exists in {table}")
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Error adding {column} to {table}: {e}")
            else:
                conn.commit()
                
        # Also create tables if they don't exist
        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS package_dishes (
                id SERIAL PRIMARY KEY,
                package_id INTEGER REFERENCES catering_packages(id) ON DELETE CASCADE,
                menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
                category_assigned VARCHAR
            );
            CREATE INDEX IF NOT EXISTS ix_package_dishes_id ON package_dishes (id);
            """)
            print("[OK] Ensured package_dishes table exists.")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Error creating package_dishes: {e}")
            traceback.print_exc()
        else:
            conn.commit()

        try:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS package_services (
                id SERIAL PRIMARY KEY,
                package_id INTEGER REFERENCES catering_packages(id) ON DELETE CASCADE,
                service_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
                quantity INTEGER DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS ix_package_services_id ON package_services (id);
            """)
            print("[OK] Ensured package_services table exists.")
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Error creating package_services: {e}")
            traceback.print_exc()
        else:
            conn.commit()
            
        cur.close()
        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Connection error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    migrate()
