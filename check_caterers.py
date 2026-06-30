import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/OccaShare")

try:
    from OccaShare.app.db import models
except ImportError:
    from app.db import models

DATABASE_URL = "postgresql://postgres:root@localhost:5432/occaserve"
if os.path.exists("OccaShare/.env"):
    with open("OccaShare/.env") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                DATABASE_URL = line.split("=")[1].strip()
                break

print("DATABASE_URL:", DATABASE_URL)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    caterers = db.query(models.CatererProfile).all()
    print(f"Total caterers in DB: {len(caterers)}")
    for c in caterers:
        print(f"ID: {c.id}, Name: {c.business_name}, Status: {c.status}, IsVerified: {c.is_verified}, AccountStatus: {c.account_status}, VerificationStatus: {c.verification_status}, PermitStatus: {c.permit_status}")
finally:
    db.close()
