import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import os
import glob
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2004@localhost:5432/occashare")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

UPLOAD_DIR = "app/static/uploads"

def get_actual_file(directory, pattern):
    """Finds a file matching the pattern in the given directory."""
    full_path_pattern = os.path.join(UPLOAD_DIR, directory, pattern)
    files = glob.glob(full_path_pattern)
    if files:
        # Return the relative URL path
        filename = os.path.basename(files[0])
        return f"/static/uploads/{directory}/{filename}"
    return None

def get_actual_files(directory, pattern):
    """Finds all files matching the pattern in the given directory."""
    full_path_pattern = os.path.join(UPLOAD_DIR, directory, pattern)
    return glob.glob(full_path_pattern)

def sync():
    db = SessionLocal()
    try:
        print("Syncing Caterer Gallery...")
        # Get all caterers who have gallery items
        caterers = db.execute(text("SELECT DISTINCT caterer_id FROM caterer_gallery")).fetchall()
        for c_row in caterers:
            cid = c_row[0]
            # Get all gallery items for this caterer
            items = db.execute(text("SELECT id, media_url FROM caterer_gallery WHERE caterer_id = :cid ORDER BY id"), {"cid": cid}).fetchall()
            # Get all actual files on disk for this caterer
            actual_files = get_actual_files("caterer", f"{cid}_gallery_*")
            if not actual_files:
                # Fallback to any gallery files if specific ones not found
                actual_files = get_actual_files("caterer", "*gallery_*")
            
            if actual_files:
                for i, item in enumerate(items):
                    gid, url = item
                    # Use modulo to distribute files if more items than files
                    chosen_file = actual_files[i % len(actual_files)]
                    new_url = f"/static/uploads/caterer/{os.path.basename(chosen_file)}"
                    
                    if url != new_url:
                        print(f"Updating Gallery {gid}: {url} -> {new_url}")
                        db.execute(text("UPDATE caterer_gallery SET media_url = :url WHERE id = :id"), {"url": new_url, "id": gid})

        print("\nSyncing Caterer Profiles...")
        res = db.execute(text("SELECT id, logo_url, cover_image_url, sample_menu_url FROM caterer_profiles;")).fetchall()
        for row in res:
            cid, logo, cover, menu = row
            # Logo
            if logo and not os.path.exists(os.path.join("app", logo.lstrip("/"))):
                actual = get_actual_files("caterer", f"{cid}_logo_*")
                if actual:
                    new_url = f"/static/uploads/caterer/{os.path.basename(actual[0])}"
                    print(f"Updating Profile {cid} (Logo): {logo} -> {new_url}")
                    db.execute(text("UPDATE caterer_profiles SET logo_url = :url WHERE id = :id"), {"url": new_url, "id": cid})
            
            # Cover
            if cover and not os.path.exists(os.path.join("app", cover.lstrip("/"))):
                actual = get_actual_files("caterer", f"{cid}_cover_*")
                if actual:
                    new_url = f"/static/uploads/caterer/{os.path.basename(actual[0])}"
                    print(f"Updating Profile {cid} (Cover): {cover} -> {new_url}")
                    db.execute(text("UPDATE caterer_profiles SET cover_image_url = :url WHERE id = :id"), {"url": new_url, "id": cid})

            # Menu
            if menu and not os.path.exists(os.path.join("app", menu.lstrip("/"))):
                actual = get_actual_files("caterer", f"{cid}_menu_*") or get_actual_files("verification", f"{cid}_menu_*")
                if not actual:
                     # Fallback to ANY menu
                     actual = get_actual_files("verification", "*menu_*")
                if actual:
                    new_url = f"/static/uploads/{'caterer' if 'caterer' in actual[0] else 'verification'}/{os.path.basename(actual[0])}"
                    print(f"Updating Profile {cid} (Menu): {menu} -> {new_url}")
                    db.execute(text("UPDATE caterer_profiles SET sample_menu_url = :url WHERE id = :id"), {"url": new_url, "id": cid})

        print("\nSyncing Identity Verifications...")
        res = db.execute(text("SELECT id, user_id, document_url, selfie_url FROM identity_verifications;")).fetchall()
        # Get some fallback files from verification folder
        all_ids = get_actual_files("verification", "*_id_*")
        all_selfies = get_actual_files("verification", "*_selfie_*")

        for row in res:
            vid, uid, doc, selfie = row
            # Doc
            if doc and not os.path.exists(os.path.join("app", doc.lstrip("/"))):
                actual = get_actual_files("verification", f"user_{uid}_id_*") or get_actual_files("verification", f"{uid}_gov_id_*")
                if not actual and all_ids:
                    actual = [all_ids[0]] # Fallback to generic ID
                
                if actual:
                    new_url = f"/static/uploads/verification/{os.path.basename(actual[0])}"
                    print(f"Updating Verification {vid} (Doc): {doc} -> {new_url}")
                    db.execute(text("UPDATE identity_verifications SET document_url = :url WHERE id = :id"), {"url": new_url, "id": vid})

            # Selfie
            if selfie and not os.path.exists(os.path.join("app", selfie.lstrip("/"))):
                actual = get_actual_files("verification", f"user_{uid}_selfie_*") or get_actual_files("verification", f"{uid}_permit_*")
                if not actual and all_selfies:
                    actual = [all_selfies[0]] # Fallback to generic selfie
                
                if actual:
                    new_url = f"/static/uploads/verification/{os.path.basename(actual[0])}"
                    print(f"Updating Verification {vid} (Selfie): {selfie} -> {new_url}")
                    db.execute(text("UPDATE identity_verifications SET selfie_url = :url WHERE id = :id"), {"url": new_url, "id": vid})

        db.commit()

        db.commit()
        print("\nSync Complete!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync()
