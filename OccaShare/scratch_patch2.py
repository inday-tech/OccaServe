import re

with open("c:\\OccaServe\\OccaShare\\app\\routers\\kyc.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the creation logic in extract_id
extract_creation = """    # Update/Create verification record as pending_confirmation
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc()).first()
    if not kyc_record or kyc_record.verification_status in ['VERIFIED', 'EXPIRED', 'rejected', 'blocked', 'verified']:
        kyc_record = models.IdentityVerification(user_id=current_user.id)
        db.add(kyc_record)"""

old_extract_creation = """    # Update/Create verification record as pending_confirmation
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc()).first()
    if not kyc_record:
        kyc_record = models.IdentityVerification(user_id=current_user.id)
        db.add(kyc_record)"""

content = content.replace(old_extract_creation, extract_creation)

# Replace the creation logic in upload_id
upload_creation = """    # Create/Update Verification Record
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc()).first()
    if not kyc_record or kyc_record.verification_status in ['VERIFIED', 'EXPIRED', 'rejected', 'blocked', 'verified']:
        kyc_record = models.IdentityVerification(user_id=current_user.id, booking_id=booking_id)
        db.add(kyc_record)
    else:
        kyc_record.booking_id = booking_id"""

old_upload_creation = """    # Create/Update Verification Record
    kyc_record = db.query(models.IdentityVerification).filter(models.IdentityVerification.user_id == current_user.id).order_by(models.IdentityVerification.created_at.desc()).first()
    if not kyc_record:
        kyc_record = models.IdentityVerification(user_id=current_user.id)
        db.add(kyc_record)"""

content = content.replace(old_upload_creation, upload_creation)

with open("c:\\OccaServe\\OccaShare\\app\\routers\\kyc.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Creation logic patched.")
