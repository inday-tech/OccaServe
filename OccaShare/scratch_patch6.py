import re

with open("c:\\OccaServe\\OccaShare\\app\\routers\\kyc.py", "r", encoding="utf-8") as f:
    content = f.read()

# Pattern to find the caterer authorization block in view_kyc_document
caterer_auth_block = """    is_caterer_authorized = False
    if current_user.role == "caterer":
        # Check if this caterer has a booking with the user whose ID this is
        try:
            parts = filename.split("_")
            target_user_id = None
            if filename.startswith("cropped_"):
                if len(parts) > 2 and parts[1] == "user":
                    target_user_id = int(parts[2])
                elif len(parts) > 3 and parts[1] == "temp" and parts[2] == "ocr":
                    target_user_id = int(parts[3])
            else:
                if len(parts) > 1 and parts[0] == "user":
                    target_user_id = int(parts[1])
                elif len(parts) > 2 and parts[0] == "temp" and parts[1] == "ocr":
                    target_user_id = int(parts[2])

            if target_user_id is not None:
                booking = db.query(models.Booking).filter(
                    models.Booking.caterer_id == current_user.caterer_profile.id,
                    models.Booking.user_id == target_user_id
                ).first()
                if booking:
                    is_caterer_authorized = True
        except Exception as parse_err:
            print(f"[KYC VIEW] Caterer authorization parsing failed: {parse_err}")"""

if caterer_auth_block in content:
    content = content.replace(caterer_auth_block, """    # Caterers are no longer authorized to view customer IDs (Platform handled)
    is_caterer_authorized = False""")
    
    # Also fix the check
    check_line = "if not (is_owner or is_admin or is_caterer_authorized):"
    new_check = "if not (is_owner or is_admin):"
    content = content.replace(check_line, new_check)
    
    with open("c:\\OccaServe\\OccaShare\\app\\routers\\kyc.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully removed caterer access to raw KYC files.")
else:
    print("Block not found. Please review manually.")
