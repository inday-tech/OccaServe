import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db import database, models
import os

def fix_logos():
    db = next(database.get_db())
    # Caterer 1 logo fix
    caterer1 = db.query(models.CatererProfile).filter(models.CatererProfile.id == 1).first()
    if caterer1:
        old_logo = caterer1.logo_url
        new_logo = "/static/uploads/caterer/1_logo_a0260ebc.png"
        print(f"Updating Caterer 1 logo from {old_logo} to {new_logo}")
        caterer1.logo_url = new_logo
    
    # Check for other potentially broken logos
    all_caterers = db.query(models.CatererProfile).all()
    for c in all_caterers:
        if c.logo_url and c.logo_url.startswith("/static/"):
            # Strip leading slash and prepend app/
            path = "app" + c.logo_url
            if not os.path.exists(path):
                print(f"Warning: Logo for {c.business_name} not found at {path}")
            else:
                print(f"Confirmed: Logo for {c.business_name} exists at {path}")
    
    db.commit()
    print("Database update complete.")

if __name__ == "__main__":
    fix_logos()
