"""
Create admin user for OccaServe deployment.
Runs during the release phase and creates the admin account if it doesn't exist.
"""

import sys
import os

# Ensure the project root (OccaShare/) is on the path when run as a module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.database import SessionLocal, engine, Base
from app.db import models
from app.core.security import get_password_hash

# Ensure all tables exist before attempting to insert
Base.metadata.create_all(bind=engine)


def create_initial_caterer(db):
    """Insert the initial caterer for occaserve.com"""
    email = "bonifaciojrandresito@gmail.com"
    password = "Bonifacio123"
    
    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        print(f"✓ Caterer user {email} already exists. Updating record.")
        user.role = 'caterer'
        user.is_verified = True
        user.is_email_verified = True
        user.status = 'active'
        user.password_hash = get_password_hash(password)
        db.commit()
    else:
        print(f"Creating caterer user: {email}...")
        user = models.User(
            email=email,
            password_hash=get_password_hash(password),
            role='caterer',
            first_name="Andresito",
            last_name="Bonifacio Jr",
            status='active',
            is_verified=True,
            is_email_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Handle Profile
    profile = db.query(models.CatererProfile).filter(models.CatererProfile.user_id == user.id).first()
    if not profile:
        print(f"Creating profile for {email}...")
        profile = models.CatererProfile(
            user_id=user.id,
            business_name="Thatalicious Catering Services",
            slug="thatalicious-catering-" + str(user.id),
            business_type="Full Service Catering",
            description="Professional catering services.",
            account_status='Active',
            verification_status='Verified',
            is_verified=True
        )
        db.add(profile)
        db.commit()
    
    # Handle IV
    iv = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == user.id).first()
    if not iv:
        print(f"Creating verification record for {email}...")
        iv = models.IdentityVerification(
            user_id=user.id,
            verification_status='approved',
            verified_at=models.func.now(),
            ocr_data={"manual_insertion": True}
        )
        db.add(iv)
        db.commit()

def create_admin():
    db = SessionLocal()
    try:
        # 1. Create Initial Caterer (as requested for occaserve.com)
        create_initial_caterer(db)

        # 2. Check if the admin account already exists
        existing = db.query(models.User).filter(models.User.email == "admin@occaserve.com").first()
        if existing:
            print("✓ Admin user already exists. Skipping creation.")
            return

        print("Creating admin user...")
        admin_user = models.User(
            email="admin@occaserve.com",
            password_hash=get_password_hash("Password123!"),
            role="admin",
            first_name="Admin",
            last_name="User",
            status="active",
            is_verified=True,
            is_email_verified=True,
        )
        db.add(admin_user)
        db.commit()

        print("✓ Admin user created successfully!")
        print("  Email:    admin@occaserve.com")
        print("  Password: Password123!")
        print("  Role:     admin")

    except Exception as e:
        db.rollback()
        print(f"✗ Failed to create admin user: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
