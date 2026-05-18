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
        
        print("Starting migration: Adding missing columns for Packages and Bilao/Tubs...")
        
        # Format: (table_name, column_name, column_definition)
        migrations = [
            # catering_packages
            ('catering_packages', 'selection_rules', 'JSONB NULL'),
            
            # menu_items
            ('menu_items', 'is_combo', 'BOOLEAN DEFAULT FALSE'),
            ('menu_items', 'max_choices', 'INTEGER DEFAULT 0'),
            ('menu_items', 'combo_options', 'JSONB NULL'),
            
            # booking_menu_items
            ('booking_menu_items', 'quantity', 'INTEGER DEFAULT 1'),
            ('booking_menu_items', 'choices', 'JSONB NULL')
        ]
        
        for table, column, definition in migrations:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")
                print(f"Added {column} to {table}")
            except psycopg2.errors.DuplicateColumn:
                conn.rollback()
                print(f"Column {column} already exists in {table}")
            except Exception as e:
                conn.rollback()
                print(f"Error adding {column} to {table}: {e}")
            else:
                conn.commit()
                
        cur.close()
        conn.close()
        print("\nMigration complete.")
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    migrate()
