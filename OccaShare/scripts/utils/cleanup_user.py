import sys
import os

# Add the project root to sys.path to import app modules
sys.path.append(os.getcwd())

from app.db.database import SessionLocal
from app.db.models import (
    User, CatererProfile, Booking, Review, Inquiry, 
    IdentityVerification, Notification, VerificationAttempt, 
    RefreshToken, AuditLog, CateringPackage, CatererGallery,
    BookingMenuItem, BookingHistory, OCRVerification,
    Promotion, Availability, Quotation, FraudFlag
)

def delete_user(email):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email {email} not found.")
            return

        user_id = user.id
        print(f"Deleting User ID {user_id} ({email})...")

        # 1. Handle Caterer-specific dependencies if user is a caterer
        caterer_profile = db.query(CatererProfile).filter(CatererProfile.user_id == user_id).first()
        if caterer_profile:
            cp_id = caterer_profile.id
            print(f"Deleting Caterer Profile ID {cp_id}...")
            
            # Delete things linked to CatererProfile
            db.query(CatererGallery).filter(CatererGallery.caterer_id == cp_id).delete()
            db.query(Promotion).filter(Promotion.caterer_id == cp_id).delete()
            db.query(Availability).filter(Availability.caterer_id == cp_id).delete()
            
            # Packages
            packages = db.query(CateringPackage).filter(CateringPackage.caterer_id == cp_id).all()
            for pkg in packages:
                # MenuItems are already set to cascade delete in models.py (line 129)
                db.delete(pkg)
            
            db.delete(caterer_profile)

        # 2. Handle Booking-related dependencies
        # First, find bookings made BY this user OR TO this user (if caterer)
        bookings = db.query(Booking).filter((Booking.user_id == user_id) | (Booking.caterer_id == (cp_id if caterer_profile else -1))).all()
        for b in bookings:
            b_id = b.id
            db.query(BookingMenuItem).filter(BookingMenuItem.booking_id == b_id).delete()
            db.query(BookingHistory).filter(BookingHistory.booking_id == b_id).delete()
            db.query(OCRVerification).filter(OCRVerification.booking_id == b_id).delete()
            db.query(Quotation).filter(Quotation.booking_id == b_id).delete()
            db.query(FraudFlag).filter(FraudFlag.booking_id == b_id).delete()
            db.query(VerificationAttempt).filter(VerificationAttempt.booking_id == b_id).delete()
            db.delete(b)

        # 3. Direct User Dependencies
        db.query(Review).filter(Review.user_id == user_id).delete()
        db.query(Inquiry).filter(Inquiry.user_id == user_id).delete()
        db.query(IdentityVerification).filter(IdentityVerification.user_id == user_id).delete()
        db.query(Notification).filter(Notification.user_id == user_id).delete()
        db.query(VerificationAttempt).filter(VerificationAttempt.user_id == user_id).delete()
        db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
        db.query(OCRVerification).filter(OCRVerification.user_id == user_id).delete()

        # 4. Finally Delete the User
        db.delete(user)
        
        db.commit()
        print(f"Successfully deleted user {email} and all related data.")

    except Exception as e:
        db.rollback()
        print(f"Error during deletion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    email_to_delete = "naomicaragay654@gmail.com"
    delete_user(email_to_delete)
