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
from sqlalchemy import func

# Ensure all tables exist before attempting to insert
Base.metadata.create_all(bind=engine)


def create_admin():
    db = SessionLocal()
    try:
        # Check if the admin account already exists
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
