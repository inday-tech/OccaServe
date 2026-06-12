import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.db.models import CatererProfile

def fix_address(address):
    if not address: return address
    parts = [p.strip() for p in address.split(",") if p.strip()]
    seen = set()
    cleaned = []
    for p in parts:
        lower_p = p.lower()
        if lower_p not in seen:
            seen.add(lower_p)
            cleaned.append(p)
    return ", ".join(cleaned)

def run_fix():
    db = SessionLocal()
    caterers = db.query(CatererProfile).all()
    count = 0
    for c in caterers:
        changed = False
        
        if c.address_details:
            new_ad = fix_address(c.address_details)
            if new_ad != c.address_details:
                c.address_details = new_ad
                changed = True
        
        if c.contact_address:
            new_ca = fix_address(c.contact_address)
            if new_ca != c.contact_address:
                c.contact_address = new_ca
                changed = True
                
        if changed:
            count += 1
            
    db.commit()
    db.close()
    print(f"Fixed {count} profiles.")

if __name__ == "__main__":
    run_fix()
