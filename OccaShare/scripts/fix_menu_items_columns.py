from sqlalchemy import create_engine, text
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding missing columns to 'menu_items' table...")
        try:
            # We add individual statements here so one failing doesn't break all of them
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS caterer_id INTEGER REFERENCES caterer_profiles(id);"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS dietary_tags VARCHAR[];"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS allergen_info VARCHAR[];"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS serving_size VARCHAR;"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_addon BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS addon_price FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE;"))
            
            conn.commit()
            print("Successfully added missing columns to menu_items.")
        except Exception as e:
            print(f"Error adding columns to menu_items: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
