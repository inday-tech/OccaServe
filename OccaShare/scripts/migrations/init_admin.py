"""
Initialize admin user for deployment (Railway, etc.)
This script runs once during release phase and creates admin account if it doesn't exist
"""

from app.db.database import SessionLocal, engine, Base
from app.db import models
from app.core import security as auth
import os

# Initialize database
Base.metadata.create_all(bind=engine)

db = SessionLocal()

def init_admin():
    try:
        # Check if admin user already exists
        existing_admin = db.query(models.User).filter_by(email="admin@occaserve.com").first()
        if existing_admin:
            print("✓ Admin user already exists.")
            # Verify it's set up correctly
            if existing_admin.status != "active":
                existing_admin.status = "active"
                existing_admin.is_email_verified = True
                existing_admin.is_verified = True
                db.commit()
                print("  → Updated status to active and verified")
            return

        print("Creating admin user...")
        
        # Hash password
        password_hash = auth.get_password_hash("admin123")
        print(f"  Password hash generated: {password_hash[:20]}...")
        
        # Create admin user
        admin_user = models.User(
            email="admin@occaserve.com",
            password_hash=password_hash,
            role="admin",
            first_name="Admin",
            last_name="User",
            status="active",
            is_email_verified=True,
            is_verified=True,
            auth_provider="email"
        )
        db.add(admin_user)
        db.commit()
        
        print("✓ Admin user created successfully!")
        print(f"  Email: admin@occaserve.com")
        print(f"  Password: admin123")
        print(f"  Role: admin")
        print(f"  Status: active")
        print(f"  Email verified: True")
        
    except Exception as e:
        print(f"✗ Error creating admin user: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_admin()
