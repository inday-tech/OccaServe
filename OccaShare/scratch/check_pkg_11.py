from sqlalchemy import create_url
from sqlalchemy.orm import sessionmaker
from app.db.database import engine, SessionLocal
from app.db import models

db = SessionLocal()
try:
    pkg = db.query(models.CateringPackage).filter(models.CateringPackage.id == 11).first()
    if pkg:
        print(f"Package ID 11 found: {pkg.name}")
        print(f"Is Active: {pkg.is_active}")
        print(f"Status: {pkg.status}")
        print(f"Caterer ID: {pkg.caterer_id}")
    else:
        print("Package ID 11 NOT found in database.")
        
    # Also check all packages for this caterer to see if there's an ID mismatch
    # Let's see if we can find any packages at all
    count = db.query(models.CateringPackage).count()
    print(f"Total packages in DB: {count}")
finally:
    db.close()
