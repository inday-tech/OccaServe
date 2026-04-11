from app.db import database, models

def check():
    db = next(database.get_db())
    caterers = db.query(models.CatererProfile).all()
    print(f"Total CatererProfiles: {len(caterers)}")
    for c in caterers:
        packages = db.query(models.CateringPackage).filter(models.CateringPackage.caterer_id == c.id).all()
        print(f"ID: {c.id}, Name: {c.business_name}, Status: {c.verification_status}, Packages: {len(packages)}")
        for p in packages:
            print(f"  - Package: {p.name}, Price: {p.price}, Active: {p.is_active}")

if __name__ == "__main__":
    check()
