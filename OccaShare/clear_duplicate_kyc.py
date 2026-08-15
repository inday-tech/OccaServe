import os
import sys
import re

# Ensure workspace root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)

from app.db.database import SQLALCHEMY_DATABASE_URL
from sqlalchemy import create_engine, text

def clear_duplicate_kyc():
    target_id_str = "7601-8372-1475-8026"
    clean_target = re.sub(r'[\s\-]', '', target_id_str)

    target_redacted = SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else SQLALCHEMY_DATABASE_URL
    print("==================================================")
    print(f"DATABASE TARGET: {target_redacted}")
    print(f"SEARCHING FOR DUPLICATE KYC RECORDS FOR ID: '{target_id_str}'")
    print("==================================================\n")

    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    with engine.begin() as conn:
        # Use raw SQL SELECT to avoid model schema mismatch errors (e.g. missing columns)
        rows = conn.execute(text("SELECT id, user_id, id_number, verification_status FROM identity_verifications")).fetchall()
        
        matching_records = []
        print(f"Total KYC records found in DB: {len(rows)}\n")

        for row in rows:
            rec_id, user_id, id_num, status = row
            num_str = str(id_num or "")
            clean_num = re.sub(r'[\s\-]', '', num_str)

            print(f"  - Record #{rec_id} | User #{user_id} | Status: '{status}' | ID Num: '{num_str}'")

            if (clean_target and clean_target in clean_num) or (target_id_str in num_str):
                matching_records.append((rec_id, user_id, status, num_str))

        if not matching_records:
            print(f"\nNo duplicate record found matching ID '{target_id_str}'.")
            return

        print(f"\nFound {len(matching_records)} matching record(s) for ID '{target_id_str}':")
        for rec_id, user_id, status, num_str in matching_records:
            print(f"  [MATCH] Record #{rec_id} (User #{user_id}, Status: '{status}')")

        print("\nDeleting duplicate KYC records from database...")
        for rec_id, user_id, status, num_str in matching_records:
            print(f"  -> Deleting Record #{rec_id} (User ID {user_id})...")
            conn.execute(text("DELETE FROM identity_verifications WHERE id = :id"), {"id": rec_id})

        print(f"\nSUCCESS: All duplicate KYC records matching ID '{target_id_str}' have been deleted!")

if __name__ == "__main__":
    clear_duplicate_kyc()
