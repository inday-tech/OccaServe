from app.db.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Add total_amount
        try:
            conn.execute(text("ALTER TABLE payouts ADD COLUMN total_amount FLOAT DEFAULT 0.0"))
            conn.commit()
            print("Added total_amount")
        except Exception as e:
            print(f"Skipped total_amount: {e}")

        # Add payout_reference
        try:
            conn.execute(text("ALTER TABLE payouts ADD COLUMN payout_reference VARCHAR"))
            conn.commit()
            print("Added payout_reference")
        except Exception as e:
            print(f"Skipped payout_reference: {e}")

        # Add requested_at
        try:
            conn.execute(text("ALTER TABLE payouts ADD COLUMN requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
            conn.commit()
            print("Added requested_at")
        except Exception as e:
            print(f"Skipped requested_at: {e}")

        # Add admin_notes
        try:
            conn.execute(text("ALTER TABLE payouts ADD COLUMN admin_notes TEXT"))
            conn.commit()
            print("Added admin_notes")
        except Exception as e:
            print(f"Skipped admin_notes: {e}")

if __name__ == "__main__":
    migrate()
