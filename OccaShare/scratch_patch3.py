import re

def add_expiry(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    expiry_logic = """
            kyc_record.verification_status = "verified"
            kyc_record.verified_at = func.now()
            
            from datetime import datetime
            from dateutil.relativedelta import relativedelta
            valid_until = datetime.now() + relativedelta(months=6)
            if kyc_record.id_expiry_date:
                id_expiry = kyc_record.id_expiry_date
                if isinstance(id_expiry, str):
                    try:
                        id_expiry = datetime.strptime(id_expiry, '%Y-%m-%d').date()
                    except:
                        pass
                if not isinstance(id_expiry, str) and id_expiry < valid_until.date():
                    valid_until = datetime.combine(id_expiry, datetime.min.time())
            kyc_record.verification_valid_until = valid_until
"""

    old_logic = """
            kyc_record.verification_status = "verified"
            kyc_record.verified_at = func.now()
"""
    
    # We use replace for safety, it will apply wherever this exact block exists
    if old_logic in content:
        content = content.replace(old_logic, expiry_logic)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Patched {filepath}")
    else:
        print(f"Block not found in {filepath}")


add_expiry("c:\\OccaServe\\OccaShare\\app\\routers\\caterer_dashboard.py")
add_expiry("c:\\OccaServe\\OccaShare\\app\\routers\\admin.py")
