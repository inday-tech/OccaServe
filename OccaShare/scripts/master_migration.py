import sys
import os
from sqlalchemy import text

# Add the project root to sys.path to allow importing from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import engine, Base
from app.db import models

def master_migration():
    print("Starting master migration...")
    
    # Ensure tables exist
    print("Ensuring all tables exist...")
    Base.metadata.create_all(bind=engine)
    
    # Manual migrations for missing columns
    print("Checking for missing columns...")
    
    with engine.begin() as conn:
        # Bookings Table
        booking_cols = [
            ("event_end_time", "TIME"),
            ("venue_province", "VARCHAR"),
            ("venue_city", "VARCHAR"),
            ("venue_barangay", "VARCHAR"),
            ("total_price", "FLOAT"),
            ("balance_due_date", "TIMESTAMP WITH TIME ZONE"),
            ("event_location", "TEXT"),
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("actual_cost", "FLOAT DEFAULT 0.0"),
            ("balance_proof_url", "VARCHAR"),
            ("reservation_fee", "DECIMAL"),
            ("expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("payout_id", "INTEGER"),
            ("payment_plan", "VARCHAR DEFAULT 'downpayment'"),
            ("ocr_verified", "BOOLEAN DEFAULT FALSE"),
            ("liveness_verified", "BOOLEAN DEFAULT FALSE"),
            ("paymongo_link_id", "VARCHAR"),
            ("paymongo_link_url", "VARCHAR"),
            ("payment_verification_data", "JSONB"),
            ("proof_image_hash", "VARCHAR")
        ]
        
        # Reviews Table
        review_cols = [
            ("recommend", "BOOLEAN DEFAULT FALSE"),
            ("was_punctual", "BOOLEAN DEFAULT FALSE"),
            ("is_highlighted", "BOOLEAN DEFAULT FALSE"),
            ("caterer_reply", "TEXT"),
            ("is_helpful", "BOOLEAN DEFAULT FALSE")
        ]
        
        # Users Table
        user_cols = [
            ("is_kyc_complete", "BOOLEAN DEFAULT FALSE"),
            ("kyc_attempts", "INTEGER DEFAULT 0"),
            ("must_change_password", "BOOLEAN DEFAULT FALSE"),
            ("is_archived", "BOOLEAN DEFAULT FALSE")
        ]
        
        # Caterer Profiles
        caterer_cols = [
            ("is_verified", "BOOLEAN DEFAULT FALSE"),
            ("primary_color", "VARCHAR DEFAULT '#2D3748'"),
            ("secondary_color", "VARCHAR DEFAULT '#4A5568'"),
            ("accent_color", "VARCHAR DEFAULT '#48BB78'"),
            ("highlight_color", "VARCHAR DEFAULT '#48BB78'"),
            ("font_family", "VARCHAR DEFAULT 'Inter'"),
            ("border_radius", "INTEGER DEFAULT 12"),
            ("sidebar_mode", "VARCHAR DEFAULT 'full'"),
            ("show_platform_logo", "BOOLEAN DEFAULT TRUE")
        ]
        
        # Menu Items
        menu_cols = [
            ("is_hidden", "BOOLEAN DEFAULT FALSE"),
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("image_url", "VARCHAR"),
            ("addon_price", "FLOAT DEFAULT 0.0"),
            ("is_addon", "BOOLEAN DEFAULT FALSE"),
            ("serving_size", "VARCHAR"),
            ("dietary_tags", "VARCHAR[]"),
            ("allergen_info", "VARCHAR[]")
        ]
        
        # Catering Packages
        package_cols = [
            ("status", "VARCHAR DEFAULT 'active'"),
            ("is_featured", "BOOLEAN DEFAULT FALSE"),
            ("service_type", "VARCHAR DEFAULT 'General'"),
            ("inclusions", "JSONB"),
            ("policies", "JSONB"),
            ("price_per_head", "FLOAT"),
            ("min_contract_amount", "FLOAT"),
            ("additional_guest_price", "FLOAT"),
            ("service_duration", "INTEGER DEFAULT 4"),
            ("overtime_fee", "FLOAT DEFAULT 0.0"),
            ("location_coverage", "VARCHAR"),
            ("internal_cost_per_pax", "FLOAT DEFAULT 0.0"),
            ("base_pax", "INTEGER DEFAULT 50"),
            ("labor_cost", "FLOAT DEFAULT 0.0"),
            ("utility_cost", "FLOAT DEFAULT 0.0"),
            ("equipment_cost", "FLOAT DEFAULT 0.0"),
            ("ingredient_total_cost", "FLOAT DEFAULT 0.0"),
            ("markup_type", "VARCHAR DEFAULT 'percentage'"),
            ("markup_value", "FLOAT DEFAULT 0.0")
        ]
        
        # Identity Verifications
        id_ver_cols = [
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("fraud_score", "INTEGER DEFAULT 0"),
            ("match_score", "FLOAT DEFAULT 0.0"),
            ("face_detected", "BOOLEAN DEFAULT FALSE"),
            ("id_detected", "BOOLEAN DEFAULT FALSE"),
            ("ip_address", "VARCHAR"),
            ("device_info", "JSONB"),
            ("liveness_status", "VARCHAR"),
            ("verified_at", "TIMESTAMP WITH TIME ZONE")
        ]
        
        # Payouts
        payout_cols = [
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("notes", "TEXT"),
            ("completed_at", "TIMESTAMP WITH TIME ZONE")
        ]
        
        # Payout Items
        payout_item_cols = [
            ("status", "VARCHAR DEFAULT 'pending'"),
            ("release_trigger", "VARCHAR DEFAULT 'on_completion'")
        ]
        
        # Website Config
        config_cols = [
            ("commission_rate", "FLOAT DEFAULT 10.0"),
            ("commission_fixed_amount", "FLOAT DEFAULT 20.0"),
            ("max_file_size_mb", "INTEGER DEFAULT 5"),
            ("maintenance_mode", "BOOLEAN DEFAULT FALSE"),
            ("maintenance_message", "TEXT")
        ]

        # Apply helper
        def add_cols(table_name, columns):
            print(f"  Migrating {table_name}...")
            for col_name, col_type in columns:
                try:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                except Exception as e:
                    print(f"    Warning: Could not add '{col_name}' to '{table_name}': {e}")

        add_cols("bookings", booking_cols)
        add_cols("reviews", review_cols)
        add_cols("users", user_cols)
        add_cols("caterer_profiles", caterer_cols)
        add_cols("menu_items", menu_cols)
        add_cols("catering_packages", package_cols)
        add_cols("identity_verifications", id_ver_cols)
        add_cols("payouts", payout_cols)
        add_cols("payout_items", payout_item_cols)
        add_cols("website_config", config_cols)
        
        # Create Social Posts table if missing
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS social_posts (
                    id SERIAL PRIMARY KEY,
                    caterer_id INTEGER REFERENCES caterer_profiles(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    image_url VARCHAR(255),
                    post_type VARCHAR(50) DEFAULT 'general',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("  Table social_posts checked/created.")
        except Exception as e:
            print(f"    Warning: social_posts creation failed: {e}")

    print("Master migration completed successfully.")

if __name__ == "__main__":
    master_migration()
