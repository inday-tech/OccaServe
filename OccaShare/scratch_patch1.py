import re

with open("c:\\OccaServe\\OccaShare\\app\\routers\\kyc.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace all `.first()` for IdentityVerification with `.order_by(models.IdentityVerification.created_at.desc()).first()`
# We do this using regex.
pattern = r'(db\.query\(models\.IdentityVerification\)\.filter\([^\)]+\))\.first\(\)'
replacement = r'\1.order_by(models.IdentityVerification.created_at.desc()).first()'

new_content = re.sub(pattern, replacement, content)

# Add logic for verification validity: + 6 months
# Look for where verification_status = "verified"
import datetime
from dateutil.relativedelta import relativedelta

verify_block = """
        # Update User & IdentityVerification records if verified
        if status == "verified":
            user.is_verified = True
            user.is_kyc_complete = True
            if kyc_record:
                kyc_record.verification_status = "VERIFIED"
                kyc_record.verified_at = func.now()
                kyc_record.failure_reason = None
                
                # Calculate expiry: 6 months from now
                from datetime import datetime
                from dateutil.relativedelta import relativedelta
                valid_until = datetime.now() + relativedelta(months=6)
                
                # Check if ID expires earlier
                if kyc_record.id_expiry_date:
                    if isinstance(kyc_record.id_expiry_date, str):
                        try:
                            id_expiry = datetime.strptime(kyc_record.id_expiry_date, '%Y-%m-%d').date()
                        except:
                            id_expiry = kyc_record.id_expiry_date
                    else:
                        id_expiry = kyc_record.id_expiry_date
                        
                    if id_expiry < valid_until.date():
                        valid_until = datetime.combine(id_expiry, datetime.min.time())
                
                kyc_record.verification_valid_until = valid_until
"""

new_content = new_content.replace("""
        # Update User & IdentityVerification records if verified
        if status == "verified":
            user.is_verified = True
            user.is_kyc_complete = True
            if kyc_record:
                kyc_record.verification_status = "verified"
                kyc_record.verified_at = func.now()
                kyc_record.failure_reason = None
""", verify_block)

# Also fix the manual verification logic if it exists (admin.py)

with open("c:\\OccaServe\\OccaShare\\app\\routers\\kyc.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("kyc.py patched")
