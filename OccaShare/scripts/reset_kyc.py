from sqlalchemy.orm import Session
from app.db import database, models

def reset_kyc_for_user(email: str):
    db = next(database.get_db())
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"User with email {email} not found.")
            return

        user.kyc_attempts = 0
        user.is_kyc_complete = False
        user.is_verified = False
        
        kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user.id).first()
        if kyc_record:
            kyc_record.verification_status = 'pending'
            kyc_record.failure_reason = None
            print(f"Reset KYC status for user: {email}")
        else:
            print(f"No KYC record found for user {email}, but attempts have been reset to 0.")
            
        db.commit()
    except Exception as e:
        print(f"Error resetting KYC: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Get the user email from the system or just reset all for testing if needed
    # For now, let's target the user 'naomi' if we can find them
    import sys
    if len(sys.argv) > 1:
        reset_kyc_for_user(sys.argv[1])
    else:
        print("Usage: python reset_kyc.py <user_email>")
