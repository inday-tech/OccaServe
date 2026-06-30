import os
import sys

# Add current directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.db.database import engine, SQLALCHEMY_DATABASE_URL

def run_migration():
    print("=" * 50)
    print("Running Database Schema Update...")
    print("=" * 50)
    
    target_log = SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL
    print(f"Connecting to database: {target_log}\n")
    
    # Define alter table statements to fix the UndefinedColumn errors
    queries = [
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_labor_cost double precision DEFAULT 0.0;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_utility_cost double precision DEFAULT 0.0;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_transport_cost double precision DEFAULT 0.0;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_reservation_type varchar DEFAULT 'fixed';",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS default_reservation_value double precision DEFAULT 0.0;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS notification_preferences jsonb DEFAULT '{\"email_new_booking\": true, \"email_payment_confirmed\": true, \"email_weekly_summary\": false, \"push_messages\": true, \"email_review_received\": true}'::jsonb;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS deactivation_reason text;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS deactivated_at timestamp with time zone;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS outstanding_balance double precision DEFAULT 0.0;",
        "ALTER TABLE caterer_profiles ADD COLUMN IF NOT EXISTS commission_rate double precision DEFAULT 0.05;"
    ]
    
    # Execute queries
    with engine.connect() as conn:
        for query in queries:
            try:
                conn.execute(text(query))
                print(f"SUCCESS: {query}")
            except Exception as e:
                print(f"ERROR executing {query}: {e}")
        
        conn.commit()
    
    print("\n" + "=" * 50)
    print("Migration completed successfully!")
    print("=" * 50)

if __name__ == "__main__":
    run_migration()
