import sys
sys.path.append(r"C:\OccaServe\OccaShare")
from app.db.database import SessionLocal
from app.db.models import CateringPackage

db = SessionLocal()
p = db.query(CateringPackage).filter(CateringPackage.id == 14).first()
if p:
    p.pricing_mode = 'fixed'
    p.price_unit = 'total'
    db.commit()
    print("Fixed package 14 to fixed price")
else:
    print("Package 14 not found")

db.close()
