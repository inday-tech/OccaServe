from app.database import engine, Base, SessionLocal
from app import models, auth
from sqlalchemy import text

def reset_database():
    print("Resetting database...")
    
    try:
        # 1. Drop all tables by recreating schema
        with engine.connect() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE;"))
            connection.execute(text("CREATE SCHEMA public;"))
            connection.commit()
        print("All tables dropped.")
    except Exception as e:
        print(f"Error dropping schema: {e}")

    try:
        # 2. Create all tables from models
        Base.metadata.create_all(bind=engine)
        print("All tables recreated.")

        # 3. Create initial Admin user
        db = SessionLocal()
        admin_email = "admin@occashare.com"
        admin_password = "admin123"
        hashed_pwd = auth.get_password_hash(admin_password)

        existing_admin = db.query(models.User).filter(models.User.email == admin_email).first()
        if not existing_admin:
            admin_user = models.User(
                email=admin_email,
                password_hash=hashed_pwd,
                role="admin",
                status="active"
            )
            db.add(admin_user)
            db.commit()
            print(f"Admin user created: {admin_email}")
        else:
            print("Admin user already exists.")
        
        db.close()
    except Exception as e:
        print(f"Error recreating tables/admin: {e}")

if __name__ == "__main__":
    reset_database()
