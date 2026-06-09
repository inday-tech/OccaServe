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
    
    if True:
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
            ("proof_image_hash", "VARCHAR"),
            ("actual_cost_breakdown", "JSONB"),
            ("special_requests", "TEXT"),
            ("caterer_notes", "TEXT"),
            ("booking_source", "VARCHAR DEFAULT 'OccaServe'"),
            ("commission_calculated", "BOOLEAN DEFAULT FALSE")
        ]
        
        # Reviews Table
        review_cols = [
            ("recommend", "BOOLEAN DEFAULT FALSE"),
            ("was_punctual", "BOOLEAN DEFAULT FALSE"),
            ("is_highlighted", "BOOLEAN DEFAULT FALSE"),
            ("caterer_reply", "TEXT"),
            ("is_helpful", "BOOLEAN DEFAULT FALSE"),
            ("is_archived", "BOOLEAN DEFAULT FALSE")
        ]
        
        # Users Table
        user_cols = [
            ("middle_name", "VARCHAR(255)"),
            ("dob", "DATE"),
            ("is_kyc_complete", "BOOLEAN DEFAULT FALSE"),
            ("kyc_attempts", "INTEGER DEFAULT 0"),
            ("must_change_password", "BOOLEAN DEFAULT FALSE"),
            ("is_archived", "BOOLEAN DEFAULT FALSE"),
            ("status_reason", "TEXT"),
            ("investigation_notes", "TEXT"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("facebook_id", "VARCHAR"),
            ("google_id", "VARCHAR"),
            ("instagram_id", "VARCHAR"),
            ("auth_provider", "VARCHAR DEFAULT 'local'"),
            ("is_email_verified", "BOOLEAN DEFAULT FALSE"),
            ("verification_code", "VARCHAR"),
            ("otp_expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("reset_token", "VARCHAR"),
            ("reset_token_expires", "TIMESTAMP WITH TIME ZONE")
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
            ("show_platform_logo", "BOOLEAN DEFAULT TRUE"),
            ("profile_views", "INTEGER DEFAULT 0"),
            ("province_code", "VARCHAR"),
            ("city_code", "VARCHAR"),
            ("brgy_code", "VARCHAR"),
            ("address_details", "TEXT"),
            ("min_pax", "INTEGER DEFAULT 0"),
            ("starting_price", "FLOAT DEFAULT 0.0"),
            ("sample_menu_url", "VARCHAR"),
            ("permit_url", "VARCHAR"),
            ("permit_status", "VARCHAR DEFAULT 'Pending'"),
            ("gov_id_url", "VARCHAR"),
            ("latitude", "FLOAT"),
            ("longitude", "FLOAT"),
            ("glass_mode", "BOOLEAN DEFAULT FALSE"),
            ("sidebar_color", "VARCHAR DEFAULT '#000000'"),
            ("header_color", "VARCHAR DEFAULT '#FFFFFF'"),
            ("dashboard_texture", "VARCHAR DEFAULT 'none'"),
            ("sidebar_decoration", "VARCHAR DEFAULT 'none'"),
            ("header_decoration", "VARCHAR DEFAULT 'none'"),
            ("terms_and_conditions", "TEXT"),
            ("booking_lead_time", "INTEGER DEFAULT 7"),
            ("equipment_turnover_hours", "INTEGER DEFAULT 24"),
            ("gcash_number", "VARCHAR"),
            ("gcash_qr_url", "VARCHAR"),
            ("maya_number", "VARCHAR"),
            ("maya_qr_url", "VARCHAR"),
            ("bank_name", "VARCHAR"),
            ("bank_account_name", "VARCHAR"),
            ("bank_account_number", "VARCHAR"),
            ("bank_qr_url", "VARCHAR"),
            ("card_bank", "VARCHAR"),
            ("card_holder_name", "VARCHAR"),
            ("card_number", "VARCHAR"),
            ("cash_instructions", "TEXT"),
            ("verification_status", "VARCHAR DEFAULT 'Pending'"),
            ("account_status", "VARCHAR DEFAULT 'Active'"),
            ("status", "VARCHAR DEFAULT 'Draft'"),
            ("team_size", "INTEGER DEFAULT 1"),
            ("notification_preferences", "JSONB"),
            ("deactivation_reason", "TEXT"),
            ("deactivated_at", "TIMESTAMP WITH TIME ZONE"),
            ("max_bookings_per_day", "INTEGER DEFAULT 1"),
            ("auto_block_enabled", "BOOLEAN DEFAULT TRUE"),
            ("outstanding_balance", "FLOAT DEFAULT 0.0"),
            ("commission_rate", "FLOAT DEFAULT 0.05")
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
            ("allergen_info", "VARCHAR[]"),
            ("cost_price", "FLOAT DEFAULT 0.0"),
            ("cost_breakdown", "JSONB"),
            ("is_combo", "BOOLEAN DEFAULT FALSE"),
            ("max_choices", "INTEGER DEFAULT 0"),
            ("combo_options", "JSONB NULL")
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
            ("markup_value", "FLOAT DEFAULT 0.0"),
            ("reservation_fee", "FLOAT DEFAULT 0.0"),
            ("booking_lead_time", "INTEGER DEFAULT 7"),
            ("cost_price", "FLOAT DEFAULT 0.0"),
            ("cost_breakdown", "JSONB"),
            ("selection_rules", "JSONB NULL")
        ]
        
        # Identity Verifications
        id_ver_cols = [
            ("verification_type", "VARCHAR DEFAULT 'government_id'"),
            ("document_url", "VARCHAR"),
            ("id_number", "VARCHAR"),
            ("selfie_url", "VARCHAR"),
            ("selfie_2_url", "VARCHAR"),
            ("selfie_3_url", "VARCHAR"),
            ("ocr_data", "JSONB"),
            ("verification_status", "VARCHAR DEFAULT 'pending'"),
            ("failure_reason", "TEXT"),
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
            ("completed_at", "TIMESTAMP WITH TIME ZONE"),
            ("total_amount", "FLOAT DEFAULT 0.0"),
            ("payout_reference", "VARCHAR"),
            ("reference_number", "VARCHAR"),
            ("admin_notes", "TEXT"),
            ("requested_at", "TIMESTAMP WITH TIME ZONE"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP")
        ]
        
        # Payout Items
        payout_item_cols = [
            ("status", "VARCHAR DEFAULT 'pending'"),
            ("release_trigger", "VARCHAR DEFAULT 'on_completion'"),
            ("commission_amount", "FLOAT DEFAULT 0.0"),
            ("payment_reference", "VARCHAR"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP")
        ]
        
        # Website Config
        config_cols = [
            ("commission_rate", "FLOAT DEFAULT 10.0"),
            ("commission_fixed_amount", "FLOAT DEFAULT 20.0"),
            ("max_file_size_mb", "INTEGER DEFAULT 5"),
            ("maintenance_mode", "BOOLEAN DEFAULT FALSE"),
            ("maintenance_message", "TEXT"),
            ("site_name", "VARCHAR DEFAULT 'OccaShare'"),
            ("support_email", "VARCHAR DEFAULT 'support@occashare.com'"),
            ("seo_description", "TEXT"),
            ("logo_url", "VARCHAR"),
            ("favicon_url", "VARCHAR"),
            ("facebook_link", "VARCHAR"),
            ("instagram_link", "VARCHAR"),
            ("twitter_link", "VARCHAR"),
            ("hero_bg_1", "VARCHAR"),
            ("hero_label_1", "VARCHAR DEFAULT 'Wedding Receptions'"),
            ("hero_bg_2", "VARCHAR"),
            ("hero_label_2", "VARCHAR DEFAULT 'Corporate Events'"),
            ("hero_bg_3", "VARCHAR"),
            ("hero_label_3", "VARCHAR DEFAULT 'Christmas Parties'"),
            ("hero_bg_4", "VARCHAR"),
            ("hero_label_4", "VARCHAR DEFAULT 'Birthdays'"),
            ("hero_bg_5", "VARCHAR"),
            ("hero_label_5", "VARCHAR DEFAULT 'Private Parties'")
        ]
        
        # Quotations
        quotation_cols = [
            ("total_amount", "FLOAT"),
            ("valid_until", "DATE"),
            ("status", "VARCHAR DEFAULT 'pending'"),
            ("notes", "TEXT"),
            ("terms_conditions", "TEXT"),
            ("caterer_signature", "TEXT"),
            ("customer_signature", "TEXT"),
            ("caterer_signed_at", "TIMESTAMP WITH TIME ZONE"),
            ("customer_signed_at", "TIMESTAMP WITH TIME ZONE"),
            ("contract_url", "VARCHAR")
        ]
        
        # Caterer Gallery
        gallery_cols = [
            ("media_type", "VARCHAR DEFAULT 'image'"),
            ("caption", "VARCHAR"),
            ("display_order", "INTEGER DEFAULT 0"),
            ("is_archived", "BOOLEAN DEFAULT FALSE")
        ]
        
        # Platform Feedback
        feedback_cols = [
            ("feedback_type", "VARCHAR"),
            ("content", "TEXT"),
            ("status", "VARCHAR DEFAULT 'pending'")
        ]

        # Booking Menu Items (Custom Selection Lists)
        booking_menu_items_cols = [
            ("quantity", "INTEGER DEFAULT 1"),
            ("choices", "JSONB NULL")
        ]

        # Apply helper
        def add_cols(table_name, columns):
            print(f"  Migrating {table_name}...")
            for col_name, col_type in columns:
                try:
                    with engine.begin() as conn:
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
        add_cols("quotations", quotation_cols)
        add_cols("caterer_gallery", gallery_cols)
        add_cols("platform_feedback", feedback_cols)
        add_cols("booking_menu_items", booking_menu_items_cols)

        # Legacy Data Migration: Sync middle_initial to middle_name
        print("  Synchronizing middle_initial data to middle_name...")
        try:
            with engine.begin() as conn:
                res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'middle_initial'")).fetchone()
                if res:
                    conn.execute(text("""
                        UPDATE users 
                        SET middle_name = middle_initial 
                        WHERE middle_name IS NULL 
                        AND middle_initial IS NOT NULL 
                        AND middle_initial != '';
                    """))
                    print("  Middle initial synchronization complete.")
                else:
                    print("  Column 'middle_initial' does not exist. Skipping synchronization.")
        except Exception as e:
            print(f"    Warning: Could not sync middle_initial data: {e}")
        
        # Create Social Posts table if missing
        try:
            with engine.begin() as conn:
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

        # Create Profile Views table for unique view tracking
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS profile_views (
                        id SERIAL PRIMARY KEY,
                        caterer_id INTEGER NOT NULL REFERENCES caterer_profiles(id) ON DELETE CASCADE,
                        viewer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """))
            print("  Table profile_views checked/created.")
            # Add unique constraint to ensure one view per user per caterer
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        CREATE UNIQUE INDEX IF NOT EXISTS uix_profile_views_caterer_viewer
                        ON profile_views (caterer_id, viewer_id);
                    """))
                print("  Unique index on profile_views created.")
            except Exception as e:
                print(f"    Warning: profile_views unique index: {e}")
        except Exception as e:
            print(f"    Warning: profile_views creation failed: {e}")

    print("Master migration completed successfully.")

if __name__ == "__main__":
    master_migration()
