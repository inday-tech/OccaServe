from sqlalchemy import text
from database import engine

def migrate_smart_pricing():
    with engine.connect() as conn:
        print("Starting Smart Pricing Migration...")
        
        # 1. Create ingredients table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ingredients (
                    id SERIAL PRIMARY KEY,
                    caterer_id INTEGER REFERENCES caterer_profiles(id),
                    name VARCHAR NOT NULL,
                    unit VARCHAR NOT NULL,
                    unit_price FLOAT DEFAULT 0.0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            conn.commit()
            print("Migration: Table 'ingredients' ensured.")
        except Exception as e:
            print(f"Migration Error on 'ingredients': {e}")
            conn.rollback()

        # 2. Create menu_item_ingredients table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS menu_item_ingredients (
                    id SERIAL PRIMARY KEY,
                    menu_item_id INTEGER REFERENCES menu_items(id) ON DELETE CASCADE,
                    ingredient_id INTEGER REFERENCES ingredients(id) ON DELETE CASCADE,
                    quantity FLOAT NOT NULL
                );
            """))
            conn.commit()
            print("Migration: Table 'menu_item_ingredients' ensured.")
        except Exception as e:
            print(f"Migration Error on 'menu_item_ingredients': {e}")
            conn.rollback()

        # 3. Add ROI/Markup columns to catering_packages
        package_columns = [
            ("markup_type", "VARCHAR DEFAULT 'percentage'"),
            ("markup_value", "FLOAT DEFAULT 0.0"),
            ("cost_price", "FLOAT DEFAULT 0.0"),
            ("cost_breakdown", "JSONB")
        ]

        for col_name, col_type in package_columns:
            try:
                conn.execute(text(f"ALTER TABLE catering_packages ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Migration: Added '{col_name}' to 'catering_packages'.")
            except Exception as e:
                # Silently skip if it already exists
                if "already exists" not in str(e).lower():
                    print(f"Migration Error on 'catering_packages.{col_name}': {e}")
                conn.rollback()

        print("Smart Pricing Migration Completed.")

if __name__ == "__main__":
    migrate_smart_pricing()
