from app.db.database import SessionLocal
from app.db import models
import random
import string

def backfill():
    db = SessionLocal()
    try:
        payouts = db.query(models.Payout).all()
        count = 0
        for p in payouts:
            # 1. Backfill total_amount from amount if missing
            if not p.total_amount or p.total_amount == 0:
                p.total_amount = p.amount
            
            # 2. Backfill payout_reference if missing
            if not p.payout_reference or p.payout_reference == "None":
                ref_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                p.payout_reference = f"WDR-{ref_suffix}"
            
            # 3. Backfill requested_at if missing
            if not p.requested_at:
                p.requested_at = p.created_at
            
            count += 1
            
        db.commit()
        print(f"Successfully backfilled {count} payout records.")
    except Exception as e:
        db.rollback()
        print(f"Error during backfill: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    backfill()
