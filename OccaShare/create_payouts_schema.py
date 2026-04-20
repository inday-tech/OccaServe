from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL
import os

def migrate():
    print(f"Connecting to database: {SQLALCHEMY_DATABASE_URL}")
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        # 1. Add columns to 'bookings'
        print("Checking/Adding Paymongo columns to 'bookings'...")
        booking_cols = [
            ("paymongo_link_id", "VARCHAR"),
            ("paymongo_link_url", "VARCHAR"),
            ("payout_id", "INTEGER")
        ]
        for col_name, col_type in booking_cols:
            try:
                conn.execute(text(f"ALTER TABLE bookings ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"  - Successfully added '{col_name}'.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  - Column '{col_name}' already exists. Skipping.")
                else:
                    print(f"  - Error adding '{col_name}': {e}")
                conn.rollback()

        # 2. Add column to 'website_config'
        print("Checking/Adding 'commission_fixed_amount' to 'website_config'...")
        try:
            conn.execute(text("ALTER TABLE website_config ADD COLUMN commission_fixed_amount FLOAT DEFAULT 20.0;"))
            conn.commit()
            print("  - Successfully added 'commission_fixed_amount'.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  - Column 'commission_fixed_amount' already exists. Skipping.")
            else:
                print(f"  - Error adding 'commission_fixed_amount': {e}")
            conn.rollback()

        # 3. Create 'payouts' table
        print("Checking/Creating 'payouts' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS payouts (
                    id SERIAL PRIMARY KEY,
                    caterer_id INTEGER REFERENCES caterer_profiles(id),
                    amount FLOAT,
                    status VARCHAR DEFAULT 'pending',
                    reference_number VARCHAR,
                    is_archived BOOLEAN DEFAULT FALSE,
                    notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    completed_at TIMESTAMP WITH TIME ZONE
                );
            """))
            conn.commit()
            print("  - Successfully created 'payouts' table.")
        except Exception as e:
            print(f"  - Error creating 'payouts' table: {e}")
            conn.rollback()

        # 4. Create 'payout_items' table
        print("Checking/Creating 'payout_items' table...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS payout_items (
                    id SERIAL PRIMARY KEY,
                    payout_id INTEGER REFERENCES payouts(id) ON DELETE CASCADE,
                    booking_id INTEGER REFERENCES bookings(id),
                    amount FLOAT,
                    status VARCHAR DEFAULT 'pending',
                    release_trigger VARCHAR DEFAULT 'on_completion'
                );
            """))
            conn.commit()
            print("  - Successfully created 'payout_items' table.")
        except Exception as e:
            print(f"  - Error creating 'payout_items' table: {e}")
            conn.rollback()

        # 5. Add foreign key index for bookings.payout_id if not exists
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bookings_payout_id ON bookings (payout_id);"))
            conn.commit()
            print("  - Successfully created index for 'payout_id'.")
        except Exception as e:
            print(f"  - Error creating index: {e}")
            conn.rollback()

    print("\nMigration process completed.")

if __name__ == "__main__":
    migrate()
