from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Adding 'service_type' column to 'catering_packages'...")
        try:
            conn.execute(text("ALTER TABLE catering_packages ADD COLUMN service_type VARCHAR DEFAULT 'General';"))
            conn.commit()
            print("Successfully added 'service_type'.")
        except Exception as e:
            print(f"Error adding 'service_type': {e}")
            conn.rollback()

        print("Adding satisfaction columns to 'reviews'...")
        try:
            conn.execute(text("ALTER TABLE reviews ADD COLUMN recommend BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE reviews ADD COLUMN was_punctual BOOLEAN DEFAULT FALSE;"))
            conn.commit()
            print("Successfully added satisfaction columns.")
        except Exception as e:
            print(f"Error adding satisfaction columns: {e}")
            conn.rollback()

        print("Adding 'balance_proof_url' to 'bookings'...")
        try:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN balance_proof_url VARCHAR;"))
            conn.commit()
            print("Successfully added 'balance_proof_url'.")
        except Exception as e:
            print(f"Error adding 'balance_proof_url': {e}")
            conn.rollback()

        print("Adding payout columns to 'caterer_profiles'...")
        try:
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN payout_method VARCHAR;"))
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN payout_account_name VARCHAR;"))
            conn.execute(text("ALTER TABLE caterer_profiles ADD COLUMN payout_account_number VARCHAR;"))
            conn.commit()
            print("Successfully added payout columns.")
        except Exception as e:
            print(f"Error adding payout columns: {e}")
            conn.rollback()

        print("Adding expanded payout columns to 'caterer_profiles'...")
        columns = [
            ("gcash_number", "VARCHAR"),
            ("gcash_qr_url", "VARCHAR"),
            ("maya_number", "VARCHAR"),
            ("bank_name", "VARCHAR"),
            ("bank_account_name", "VARCHAR"),
            ("bank_account_number", "VARCHAR"),
            ("cash_instructions", "TEXT"),
            ("card_bank", "VARCHAR"),
            ("card_holder_name", "VARCHAR"),
            ("card_number", "VARCHAR")
        ]
        for col_name, col_type in columns:
            try:
                conn.execute(text(f"ALTER TABLE caterer_profiles ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Successfully added '{col_name}'.")
            except Exception as e:
                print(f"Error adding '{col_name}': {e}")
                conn.rollback()

        print("Adding policy columns to 'caterer_profiles'...")
        policy_columns = [
            ("booking_policy", "TEXT"),
            ("payment_policy", "TEXT"),
            ("cancellation_policy", "TEXT")
        ]
        for col_name, col_type in policy_columns:
            try:
                conn.execute(text(f"ALTER TABLE caterer_profiles ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Successfully added '{col_name}'.")
            except Exception as e:
                print(f"Error adding '{col_name}': {e}")
                conn.rollback()

        print("Adding 'link' column to 'notifications'...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    title VARCHAR,
                    message TEXT,
                    type VARCHAR DEFAULT 'info',
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """))
            conn.commit()
            
            conn.execute(text("ALTER TABLE notifications ADD COLUMN link VARCHAR;"))
            conn.commit()
            print("Successfully added 'link' to notifications.")
        except Exception as e:
            print(f"Error adding 'link' to notifications: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
