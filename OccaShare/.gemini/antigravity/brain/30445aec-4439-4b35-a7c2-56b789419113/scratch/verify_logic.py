from app.db import database, models
from sqlalchemy import or_

def test_rejection_logic():
    db = next(database.get_db())
    try:
        # 1. Test Downpayment Rejection
        # Find a booking with proof_submitted
        b1 = db.query(models.Booking).filter(models.Booking.payment_status == 'proof_submitted').first()
        if b1:
            print(f"Testing Downpayment Rejection for Booking #{b1.id}")
            # Mock the request_new_proof logic
            b1.payment_status = 'reupload_requested'
            b1.payment_proof_url = None
            db.commit()
            
            # Re-fetch and verify
            b1 = db.query(models.Booking).get(b1.id)
            print(f"Result: payment_status={b1.payment_status}, proof_url={b1.payment_proof_url}")
            assert b1.payment_status == 'reupload_requested'
            assert b1.payment_proof_url is None
        else:
            print("No 'proof_submitted' booking found for testing.")

        # 2. Test Balance Rejection
        # Find a booking with balance_proof_submitted
        b2 = db.query(models.Booking).filter(models.Booking.payment_status == 'balance_proof_submitted').first()
        if b2:
            print(f"Testing Balance Rejection for Booking #{b2.id}")
            b2.payment_status = 'balance_reupload_requested'
            b2.balance_proof_url = None
            db.commit()
            
            # Re-fetch and verify
            b2 = db.query(models.Booking).get(b2.id)
            print(f"Result: payment_status={b2.payment_status}, balance_url={b2.balance_proof_url}")
            assert b2.payment_status == 'balance_reupload_requested'
            assert b2.balance_proof_url is None
        else:
            print("No 'balance_proof_submitted' booking found for testing.")
            
    finally:
        db.close()

if __name__ == "__main__":
    test_rejection_logic()
