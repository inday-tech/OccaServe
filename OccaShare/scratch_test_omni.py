import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import CatererProfile, User

def test():
    db = SessionLocal()
    user = db.query(User).filter(User.role == "caterer").first()
    if not user:
        print("No caterer found")
        return

    q = "test"
    query = q.lower().strip()
    profile = user.caterer_profile
    if not profile:
        print("No profile found")
        return

    results = []
    print("Testing caterer_omni_search logic...")
    print(f"Profile ID: {profile.id}")
    
    # Check imports that might fail in caterer_dashboard.py
    import time
    
    try:
        from app.models import Booking, MenuItem, CateringPackage
        # 1. Search Bookings
        bookings = db.query(Booking).filter(
            Booking.caterer_id == profile.id
        ).all()
        print(f"Found {len(bookings)} bookings")
        
        # 2. Search Menu Items
        menu_items = db.query(MenuItem).filter(
            MenuItem.caterer_id == profile.id,
            MenuItem.is_archived == False
        ).all()
        print(f"Found {len(menu_items)} menu items")
        
        # 3. Search Packages
        packages = db.query(CateringPackage).filter(
            CateringPackage.caterer_id == profile.id,
            CateringPackage.status != "archived"
        ).all()
        print(f"Found {len(packages)} packages")
        
        # 4. Search Customers
        customers = db.query(User).join(Booking, Booking.customer_id == User.id).filter(
            Booking.caterer_id == profile.id
        ).distinct().all()
        print(f"Found {len(customers)} customers")
        
        print("Success")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test()
