from sqlalchemy import create_engine, text
from app.db.database import SQLALCHEMY_DATABASE_URL

def repair():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.connect() as conn:
        print("Starting Schema Repair...")
        
        # Repair payout_items
        payout_item_cols = [
            ("status", "VARCHAR DEFAULT 'pending'"),
            ("release_trigger", "VARCHAR DEFAULT 'on_completion'")
        ]
        for col, col_type in payout_item_cols:
            try:
                conn.execute(text(f"ALTER TABLE payout_items ADD COLUMN {col} {col_type};"))
                conn.commit()
                print(f"  - Added '{col}' to payout_items.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  - '{col}' in payout_items already exists.")
                else:
                    print(f"  - Error adding '{col}' to payout_items: {e}")
                conn.rollback()

        # Repair payouts (just in case)
        payout_cols = [
            ("status", "VARCHAR DEFAULT 'pending'"),
            ("reference_number", "VARCHAR"),
            ("notes", "TEXT")
        ]
        for col, col_type in payout_cols:
            try:
                conn.execute(text(f"ALTER TABLE payouts ADD COLUMN {col} {col_type};"))
                conn.commit()
                print(f"  - Added '{col}' to payouts.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"  - '{col}' in payouts already exists.")
                else:
                    print(f"  - Error adding '{col}' to payouts: {e}")
                conn.rollback()

        print("Schema Repair Completed.")

if __name__ == "__main__":
    repair()
