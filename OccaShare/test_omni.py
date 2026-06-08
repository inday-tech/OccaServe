import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.db.models import CatererProfile, User, Booking, MenuItem, CateringPackage

def test():
    db = SessionLocal()
    profile = db.query(CatererProfile).first()
    if not profile:
        print("No profile found")
        return
    
    user = profile.user
    q = "test"
    query = q.lower().strip()
    results = []
    print("Testing caterer_omni_search logic...")
    print(f"Profile ID: {profile.id}")
    
    try:
        # 1. Search Bookings
        bookings = db.query(Booking).filter(
            Booking.caterer_id == profile.id
        ).all()
        print(f"Found {len(bookings)} bookings")
        for b in bookings:
            b_ref = str(b.id)
            b_name = f"{b.user.first_name} {b.user.last_name}".lower() if b.user else ""
            b_type = b.event_type.lower() if b.event_type else ""
            b_status = b.status.lower() if b.status else ""
            if query in b_ref or query in b_name or query in b_type or query in b_status:
                results.append({"type": "Booking"})

        print("Bookings passed")

        # 2. Search Menu Items
        menu_items = db.query(MenuItem).filter(
            MenuItem.caterer_id == profile.id,
            MenuItem.is_archived == False
        ).all()
        print(f"Found {len(menu_items)} menu items")
        for item in menu_items:
            i_name = item.name.lower() if item.name else ""
            if query in i_name:
                results.append({
                    "subtitle": f"₱{item.price:,.2f} • {item.category}",
                })
        print("Menu items passed")

        # 3. Search Packages
        packages = db.query(CateringPackage).filter(
            CateringPackage.caterer_id == profile.id,
            CateringPackage.status != "archived"
        ).all()
        print(f"Found {len(packages)} packages")
        for pkg in packages:
            p_name = pkg.name.lower() if pkg.name else ""
            if query in p_name:
                results.append({
                    "subtitle": f"₱{pkg.price_per_head:,.2f}/head",
                })
        print("Packages passed")

        # 4. Search Customers
        customers = db.query(User).join(Booking, Booking.customer_id == User.id).filter(
            Booking.caterer_id == profile.id
        ).distinct().all()
        print(f"Found {len(customers)} customers")
        for c in customers:
            c_name = f"{c.first_name} {c.last_name}".lower()
            c_email = c.email.lower()
            if query in c_name or query in c_email:
                results.append({
                    "type": "Customer",
                })
        print("Customers passed")

        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test()
