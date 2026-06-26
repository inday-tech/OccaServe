import sys
sys.path.append(r"C:\OccaServe\OccaShare")
from app.db.database import SessionLocal
from app.db.models import CateringPackage

db = SessionLocal()
packages = db.query(CateringPackage).all()
for p in packages:
    print(f"ID: {p.id}, Name: {p.name}, Mode: {p.pricing_mode}, Unit: {p.price_unit}, Price: {p.price}, PPH: {p.price_per_head}")
db.close()
