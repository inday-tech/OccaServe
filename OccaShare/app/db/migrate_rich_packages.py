from sqlalchemy import create_engine, text
from app.db.database import engine
from app.db.models import Base

def migrate():
    # 1. Ensure tables exist
    print("Ensuring tables exist...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Add new columns
    with engine.connect() as conn:
        print("Migrating 'catering_packages'...")
        columns_package = [
            ("price_per_head", "FLOAT"),
            ("min_contract_amount", "FLOAT"),
            ("additional_guest_price", "FLOAT"),
            ("service_duration", "INTEGER DEFAULT 4"),
            ("overtime_fee", "FLOAT DEFAULT 0.0"),
            ("location_coverage", "VARCHAR"),
            ("inclusions", "JSONB"),
            ("policies", "JSONB"),
            ("max_guests", "INTEGER"),
            ("status", "VARCHAR DEFAULT 'active'"),
            ("is_featured", "BOOLEAN DEFAULT FALSE")
        ]
        
        for col_name, col_type in columns_package:
            try:
                conn.execute(text(f"ALTER TABLE catering_packages ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to catering_packages.")
            except Exception as e:
                print(f"Skipped {col_name} (likely exists): {e}")
                conn.rollback()

        print("Migrating 'menu_items'...")
        columns_menu = [
            ("description", "TEXT"),
            ("dietary_tags", "VARCHAR[]"),
            ("allergen_info", "VARCHAR[]"),
            ("serving_size", "VARCHAR"),
            ("image_url", "VARCHAR")
        ]
        
        for col_name, col_type in columns_menu:
            try:
                conn.execute(text(f"ALTER TABLE menu_items ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to menu_items.")
            except Exception as e:
                print(f"Skipped {col_name} (likely exists): {e}")
                conn.rollback()

if __name__ == "__main__":
    migrate()
