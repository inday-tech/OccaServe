from app.db.database import SessionLocal, engine, Base
from app.db import models
from app.core import security as auth
import random
from datetime import datetime, timedelta

# Initialize database
Base.metadata.create_all(bind=engine)

db = SessionLocal()

def seed_data():
    try:
        # Check if users exist to avoid duplicate seeding
        if db.query(models.User).filter_by(email="admin@occaserve.com").first():
            print("Data appears to be already seeded. Skipping.")
            return

        print("Seeding data...")

        # 1. Create Users (Caterers & Customers)
        # ---------------------------------------------------------
        
        # Admin
        admin_user = models.User(
            email="admin@occaserve.com",
            password_hash=auth.get_password_hash("admin123"),
            role="admin",
            first_name="Admin",
            last_name="User",
            status="active",
            is_verified=True
        )
        db.add(admin_user)

        # Caterer 1: Gourmet Delight
        caterer1_user = models.User(
            email="gourmet@occaserve.com",
            password_hash=auth.get_password_hash("caterer123"),
            role="caterer",
            first_name="Gourmet",
            last_name="Chef",
            status="active",
            is_verified=True
        )
        db.add(caterer1_user)

        # Caterer 2: Urban Feast
        caterer2_user = models.User(
            email="urban@occaserve.com",
            password_hash=auth.get_password_hash("caterer123"),
            role="caterer",
            first_name="Urban",
            last_name="Cook",
            status="active",
            is_verified=True
        )
        db.add(caterer2_user)

        # Customer
        customer_user = models.User(
            email="customer@occaserve.com",
            password_hash=auth.get_password_hash("customer123"),
            role="customer",
            first_name="Alice",
            last_name="Customer",
            status="active",
            is_verified=True
        )
        db.add(customer_user)
        
        db.commit()
        db.refresh(caterer1_user)
        db.refresh(caterer2_user)
        db.refresh(customer_user)

        # 2. Create Caterer Profiles
        # ---------------------------------------------------------
        caterer1_profile = models.CatererProfile(
            user_id=caterer1_user.id,
            business_name="Gourmet Delight",
            slug="gourmet-delight",
            description="Exquisite flavors for every occasion. Specializing in weddings and corporate events with a touch of elegance.",
            logo_url="https://ui-avatars.com/api/?name=Gourmet+Delight&background=4f46e5&color=fff",
            cover_image_url="https://images.unsplash.com/photo-1414235077428-338989a2e8c0?q=80&w=2070&auto=format&fit=crop",
            contact_phone="+1 555-0101",
            contact_address="123 Culinary Ave, New York, NY",
            city="New York",
            rating=4.9,
            review_count=120,
            is_verified=True
        )
        db.add(caterer1_profile)

        caterer2_profile = models.CatererProfile(
            user_id=caterer2_user.id,
            business_name="Urban Feast",
            slug="urban-feast",
            description="Modern fusion cuisine that brings the street food vibe to your high-end events.",
            logo_url="https://ui-avatars.com/api/?name=Urban+Feast&background=10b981&color=fff",
            cover_image_url="https://images.unsplash.com/photo-1555244162-803834f70033?q=80&w=2070&auto=format&fit=crop",
            contact_phone="+1 555-0102",
            contact_address="456 Fusion Blvd, San Francisco, CA",
            city="San Francisco",
            rating=4.7,
            review_count=85,
            is_verified=True
        )
        db.add(caterer2_profile)
        
        db.commit()
        db.refresh(caterer1_profile)
        db.refresh(caterer2_profile)

        # 3. Create Packages
        # ---------------------------------------------------------
        packages = [
            # Gourmet Delight Packages
            {
                "caterer_id": caterer1_profile.id,
                "name": "Classic Buffet",
                "description": "A delightful selection of classic dishes suitable for any gathering. Includes 2 appetizers, 3 main courses, and dessert.",
                "price": 45.0,
                "price_unit": "per_guest",
                "min_guests": 20,
                "max_guests": 200,
                "image_url": "https://images.unsplash.com/photo-1555244162-803834f70033?q=80&w=2070&auto=format&fit=crop"
            },
            {
                "caterer_id": caterer1_profile.id,
                "name": "Premium Plated",
                "description": "An elegant 3-course sit-down dinner service. Perfect for weddings and formal corporate events.",
                "price": 85.0,
                "price_unit": "per_guest",
                "min_guests": 50,
                "max_guests": 150,
                "image_url": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?q=80&w=2070&auto=format&fit=crop"
            },
            # Urban Feast Packages
            {
                "caterer_id": caterer2_profile.id,
                "name": "Street Food Party",
                "description": "Live cooking stations featuring tacos, sliders, and skewers.",
                "price": 35.0,
                "price_unit": "per_guest",
                "min_guests": 30,
                "image_url": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?q=80&w=2071&auto=format&fit=crop"
            }
        ]

        for pkg in packages:
            db_pkg = models.CateringPackage(**pkg)
            db.add(db_pkg)
            
        # 4. Create Gallery Items
        # ---------------------------------------------------------
        gallery_items = [
            {
                "caterer_id": caterer1_profile.id,
                "media_url": "https://images.unsplash.com/photo-1519225421980-715cb0202128?q=80&w=2070&auto=format&fit=crop",
                "caption": "Wedding Cake Setup"
            },
            {
                "caterer_id": caterer1_profile.id,
                "media_url": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=2070&auto=format&fit=crop",
                "caption": "Buffet Spread"
            }
        ]
        
        for item in gallery_items:
            db_item = models.CatererGallery(**item)
            db.add(db_item)

        # 5. Create Reviews
        # ---------------------------------------------------------
        from datetime import UTC
        review1 = models.Review(
            user_id=customer_user.id,
            caterer_id=caterer1_profile.id,
            rating=5,
            comment="Absolutely verified and amazing service! The food was top notch.",
            created_at=datetime.now(UTC) - timedelta(days=2)
        )
        db.add(review1)

        db.commit()
        print("Seed data added successfully!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
