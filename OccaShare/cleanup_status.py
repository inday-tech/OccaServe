from app.db import database, models

def fix():
    db = next(database.get_db())
    caterers = db.query(models.CatererProfile).all()
    print(f"Checking {len(caterers)} caterer profiles...")
    for c in caterers:
        old_status = c.verification_status
        # Ensure it's exactly "Verified" if it's already some variation
        if old_status and old_status.strip().lower() == "verified":
             c.verification_status = "Verified"
             c.is_verified = True
             print(f"Fixed status for {c.business_name}: '{old_status}' -> 'Verified'")
        else:
             print(f"Caterer {c.business_name} has status: '{old_status}'")
    db.commit()

if __name__ == "__main__":
    fix()
