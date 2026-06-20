from sqlalchemy import text
from app.db.database import engine

def migrate_menu_v2():
    print("Starting Menu V2.0 Database Migration...")
    
    with engine.begin() as conn:
        print("1. Adding new columns to menu_items table...")
        try:
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS usage_type VARCHAR DEFAULT 'both';"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS available_for_package BOOLEAN DEFAULT TRUE;"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS available_for_order BOOLEAN DEFAULT TRUE;"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS pricing_type VARCHAR DEFAULT 'fixed';"))
            
            # Make price nullable if it isn't already
            conn.execute(text("ALTER TABLE menu_items ALTER COLUMN price DROP NOT NULL;"))
            print("Successfully added new columns.")
        except Exception as e:
            print(f"Notice during column addition (might already exist): {e}")

        print("2. Creating menu_size_pricing table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS menu_size_pricing (
                    id SERIAL PRIMARY KEY,
                    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
                    size_name VARCHAR NOT NULL,
                    capacity VARCHAR,
                    price FLOAT DEFAULT 0.0
                );
            """))
            print("Successfully created menu_size_pricing table.")
        except Exception as e:
            print(f"Error creating menu_size_pricing: {e}")

        print("3. Creating menu_weight_pricing table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS menu_weight_pricing (
                    id SERIAL PRIMARY KEY,
                    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
                    weight_label VARCHAR NOT NULL,
                    price FLOAT DEFAULT 0.0
                );
            """))
            print("Successfully created menu_weight_pricing table.")
        except Exception as e:
            print(f"Error creating menu_weight_pricing: {e}")

    print("Menu V2.0 Database Migration Completed!")

if __name__ == "__main__":
    migrate_menu_v2()
