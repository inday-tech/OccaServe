import sys
import os
from datetime import date, timedelta
from sqlalchemy import create_all
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.getcwd())

from app.db import database, models
from app.services.verification import verification_service

def test_verification_logic():
    print("Testing Enhanced Verification Logic...")
    
    # Setup - Use existing DB but mock users
    db = next(database.get_db())
    
    try:
        # Create a test user
        test_user = models.User(
            email=f"test_verify_{os.urandom(4).hex()}@example.com",
            password_hash="hashed",
            role="customer",
            is_verified=False,
            is_kyc_complete=False
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"Test User ID: {test_user.id}")
        
        # 1. New User Check
        status = verification_service.check_verification_status(test_user, db)
        print(f"Condition: New User -> Expected: FULL_VERIFICATION_REQUIRED, Got: {status}")
        assert status == "FULL_VERIFICATION_REQUIRED"
        
        # 2. Verified User Check
        test_user.is_verified = True
        test_user.is_kyc_complete = True
        kyc = models.IdentityVerification(
            user_id=test_user.id,
            verification_status="approved",
            id_expiry_date=date.today() + timedelta(days=365)
        )
        db.add(kyc)
        db.commit()
        
        status = verification_service.check_verification_status(test_user, db)
        print(f"Condition: Verified User (Valid ID) -> Expected: VERIFIED, Got: {status}")
        assert status == "VERIFIED"
        
        # 3. ID Expired Check
        kyc.id_expiry_date = date.today() - timedelta(days=1)
        db.commit()
        
        status = verification_service.check_verification_status(test_user, db)
        print(f"Condition: ID Expired -> Expected: FULL_VERIFICATION_REQUIRED, Got: {status}")
        assert status == "FULL_VERIFICATION_REQUIRED"
        
        # 4. Security Trigger Check
        kyc.id_expiry_date = date.today() + timedelta(days=365)
        test_user.security_flag = True
        db.commit()
        
        status = verification_service.check_verification_status(test_user, db)
        print(f"Condition: Security Trigger -> Expected: LIVENESS_REQUIRED, Got: {status}")
        assert status == "LIVENESS_REQUIRED"
        
        # Cleanup
        db.delete(kyc)
        db.delete(test_user)
        db.commit()
        
        print("\nSUCCESS: All verification conditions passed logic check.")
        
    except Exception as e:
        print(f"\nFAILURE: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_verification_logic()
