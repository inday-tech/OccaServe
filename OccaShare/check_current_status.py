import sys, os
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.db import models

db = SessionLocal()
try:
    print("Checking Verification Session:")
    sessions = db.query(models.VerificationSession).order_by(models.VerificationSession.created_at.desc()).limit(5).all()
    for s in sessions:
        print(f"Session ID: {s.id}, User ID: {s.user_id}, Status: {s.status}, Created: {s.created_at}")
        
    print("\nChecking Identity Verification:")
    ivs = db.query(models.IdentityVerification).order_by(models.IdentityVerification.id.desc()).limit(5).all()
    for iv in ivs:
         print(f"IV ID: {iv.id}, User ID: {iv.user_id}, Status: {iv.verification_status}, ID type: {iv.verification_type}")

    print("\nChecking Booking:")
    bookings = db.query(models.Booking).filter(models.Booking.id == 31).all()
    for b in bookings:
         print(f"Booking ID: {b.id}, User ID: {b.user_id}, OCR Verified: {b.ocr_verified}, Liveness Verified: {b.liveness_verified}")
         
    # Let's see the user email for User ID 51
    u = db.query(models.User).filter(models.User.id == 51).first()
    if u:
        print(f"\nUser 51: {u.first_name} {u.last_name}, Role: {u.role}, Email: {u.email}, Verified: {u.is_verified}")

    u_31 = db.query(models.User).filter(models.User.id == 31).first()
    if u_31:
        print(f"User 31: {u_31.first_name} {u_31.last_name}, Role: {u_31.role}, Email: {u_31.email}, Verified: {u_31.is_verified}")
finally:
    db.close()
