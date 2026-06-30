import sys
from app.db.database import SessionLocal, engine
from sqlalchemy import text

def upgrade():
    db = SessionLocal()
    try:
        # Check if delivery_zones table exists
        result = db.execute(text("SELECT to_regclass('public.delivery_zones')")).scalar()
        
        if not result:
            print("Creating delivery_zones table...")
            db.execute(text("""
            CREATE TABLE delivery_zones (
                id SERIAL PRIMARY KEY,
                caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
                province VARCHAR NOT NULL,
                city_municipality VARCHAR NOT NULL,
                barangay VARCHAR,
                fee FLOAT DEFAULT 0.0,
                is_manual_quote BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
            """))
            db.execute(text("CREATE INDEX ix_delivery_zones_id ON delivery_zones (id)"))
            print("Table created.")

        # Add new columns to caterer_profiles
        try:
            db.execute(text("ALTER TABLE caterer_profiles ADD COLUMN delivery_fee_type VARCHAR DEFAULT 'area'"))
            db.execute(text("ALTER TABLE caterer_profiles ADD COLUMN base_delivery_fee FLOAT DEFAULT 150.0"))
            db.execute(text("ALTER TABLE caterer_profiles ADD COLUMN out_of_coverage_action VARCHAR DEFAULT 'reject'"))
            print("Added delivery settings to caterer_profiles.")
        except Exception as e:
            print(f"Columns might already exist in caterer_profiles: {e}")

        # Add new columns to bookings
        try:
            db.execute(text("ALTER TABLE bookings ADD COLUMN travel_fee FLOAT DEFAULT 0.0"))
            db.execute(text("ALTER TABLE bookings ADD COLUMN travel_fee_status VARCHAR DEFAULT 'confirmed'"))
            print("Added travel_fee to bookings.")
        except Exception as e:
            print(f"Columns might already exist in bookings: {e}")
            
        db.commit()
        print("Migration successful.")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    upgrade()
