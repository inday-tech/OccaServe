from app.database import SessionLocal
from app import models, auth
import sys

def create_admin():
    db = SessionLocal()
    try:
        email = "admin@occaserve.com"
        password = "Password123!"
        
        # Check if exists
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            print(f"Admin user {email} already exists. Updating status and password...")
            existing.password_hash = auth.get_password_hash(password)
            existing.is_email_verified = True
            existing.is_verified = True
            db.commit()
            print(f"Password updated to: {password}")
            return

        hashed_password = auth.get_password_hash(password)
        
        admin_user = models.User(
            email=email,
            password_hash=hashed_password,
            role="admin",
            first_name="System",
            last_name="Admin",
            status="active",
            is_verified=True,
            is_email_verified=True
        )
        
        db.add(admin_user)
        db.commit()
        print(f"Admin user created successfully.\nEmail: {email}\nPassword: {password}")
        
    except Exception as e:
        print(f"Error creating admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
