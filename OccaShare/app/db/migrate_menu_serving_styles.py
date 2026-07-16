import asyncio
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import sys
import os

# Ensure the app module is importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.db.database import SQLALCHEMY_DATABASE_URL, engine
from app.db.models import MenuItem

# Mapping legacy categories to serving styles
LEGACY_SERVING_STYLES = [
    "party tray", "bilao", "packed meal", "crew meal", 
    "solo order", "per kilo", "whole order", "package only"
]

def migrate_serving_styles():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    print("Starting MenuItem Serving Styles Migration...")
    
    with engine.begin() as conn:
        print("Checking if serving_styles column exists...")
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='menu_items' AND column_name='serving_styles';
        """))
        if not result.fetchone():
            print("Adding serving_styles column to menu_items...")
            conn.execute(text("ALTER TABLE menu_items ADD COLUMN serving_styles VARCHAR[];"))
        else:
            print("serving_styles column already exists.")

    with SessionLocal() as session:
        # Fetch all menu items
        result = session.execute(text("SELECT id, category FROM menu_items"))
        menu_items = result.fetchall()
        
        updates = 0
        for item in menu_items:
            item_id = item[0]
            category = item[1]
            
            if not category:
                continue
                
            cat_lower = category.lower().strip()
            new_styles = []
            
            # Check if current category matches a serving style
            matched_style = next((style for style in LEGACY_SERVING_STYLES if style in cat_lower), None)
            
            if matched_style:
                # Add to serving styles array
                # Proper case
                style_proper = matched_style.title()
                if style_proper == "Package Only": 
                    pass 
                else:
                    new_styles.append(style_proper)
                    
                # Revert category to "Others"
                session.execute(
                    text("UPDATE menu_items SET category = :cat, serving_styles = :styles WHERE id = :id"),
                    {"cat": "Others", "styles": new_styles, "id": item_id}
                )
                updates += 1
                print(f"Migrated menu item {item_id}: category '{category}' -> serving_styles {new_styles}, category 'Others'")

        session.commit()
        print(f"Migration completed! Updated {updates} menu items.")
        
    engine.dispose()

if __name__ == "__main__":
    migrate_serving_styles()
