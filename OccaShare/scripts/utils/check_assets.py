import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:2004@localhost:5432/occashare")
engine = create_engine(DATABASE_URL)

def check():
    with engine.connect() as conn:
        print("--- Caterer Gallery ---")
        res = conn.execute(text("SELECT id, caterer_id, media_url FROM caterer_gallery LIMIT 10;"))
        for row in res:
            print(f"ID: {row[0]}, Caterer: {row[1]}, URL: {row[2]}")

        print("\n--- Caterer Profile ---")
        res = conn.execute(text("SELECT id, business_name, logo_url, cover_image_url FROM caterer_profiles LIMIT 10;"))
        for row in res:
            print(f"ID: {row[0]}, Name: {row[1]}, Logo: {row[2]}, Cover: {row[3]}")

        print("\n--- Identity Verification ---")
        res = conn.execute(text("SELECT id, user_id, document_url, selfie_url FROM identity_verifications LIMIT 10;"))
        for row in res:
            print(f"ID: {row[0]}, User: {row[1]}, Doc: {row[2]}, Selfie: {row[3]}")

if __name__ == "__main__":
    check()
