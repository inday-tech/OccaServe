from app.db import database, models
from sqlalchemy.orm import Session

def delete_user_and_data(email: str):
    db = next(database.get_db())
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"User {email} not found.")
            return

        user_id = user.id
        
        # 1. Independent User Records
        db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user_id).delete()
        db.query(models.VerificationAttempt).filter(models.VerificationAttempt.user_id == user_id).delete()
        db.query(models.Notification).filter(models.Notification.user_id == user_id).delete()
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete()
        db.query(models.AuditLog).filter(models.AuditLog.user_id == user_id).delete()
        db.query(models.Inquiry).filter(models.Inquiry.user_id == user_id).delete()
        db.query(models.Review).filter(models.Review.user_id == user_id).delete()
        db.query(models.OCRVerification).filter(models.OCRVerification.user_id == user_id).delete()

        # 2. Bookings and their dependencies
        bookings = db.query(models.Booking).filter(models.Booking.user_id == user_id).all()
        for b in bookings:
            db.query(models.PayoutItem).filter(models.PayoutItem.booking_id == b.id).delete()
            db.query(models.BookingMenuItem).filter(models.BookingMenuItem.booking_id == b.id).delete()
            db.query(models.BookingHistory).filter(models.BookingHistory.booking_id == b.id).delete()
            db.query(models.Quotation).filter(models.Quotation.booking_id == b.id).delete()
            db.query(models.OCRVerification).filter(models.OCRVerification.booking_id == b.id).delete()
            db.query(models.VerificationAttempt).filter(models.VerificationAttempt.booking_id == b.id).delete()
            db.query(models.FraudFlag).filter(models.FraudFlag.booking_id == b.id).delete()
            db.query(models.Review).filter(models.Review.booking_id == b.id).delete()
            db.delete(b)

        # 3. Caterer Profile (if any)
        # Check if they have a caterer profile
        profile = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == user_id).first()
        if profile:
             # This would be much more complex to delete (packages, gallery, etc)
             # But for customers, this is unlikely.
             db.delete(profile)

        # 4. Final User Deletion
        db.delete(user)
        db.commit()
        print(f"Successfully deleted user: {email}")
    except Exception as e:
        db.rollback()
        print(f"Failed to delete {email}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    emails = [
        'naomicaragay654@gmail.com',
        'theday729@gmail.com',
        '123@gmail.com',
        'dadaycaragay@gmail.com'
    ]
    for e in emails:
        delete_user_and_data(e)
