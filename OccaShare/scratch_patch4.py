import re

def add_expiry_admin():
    filepath = "c:\\OccaServe\\OccaShare\\app\\routers\\admin.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    expiry_logic_1 = """        kyc.verification_status = "verified"
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        valid_until = datetime.now() + relativedelta(months=6)
        if hasattr(kyc, 'id_expiry_date') and kyc.id_expiry_date:
            id_expiry = kyc.id_expiry_date
            if isinstance(id_expiry, str):
                try: id_expiry = datetime.strptime(id_expiry, '%Y-%m-%d').date()
                except: pass
            if not isinstance(id_expiry, str) and id_expiry < valid_until.date():
                valid_until = datetime.combine(id_expiry, datetime.min.time())
        kyc.verification_valid_until = valid_until
        kyc.failure_reason = None"""

    old_logic_1 = """        kyc.verification_status = "verified"
        kyc.failure_reason = None"""

    expiry_logic_2 = """        kyc.verification_status = "verified"
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        valid_until = datetime.now() + relativedelta(months=6)
        if hasattr(kyc, 'id_expiry_date') and kyc.id_expiry_date:
            id_expiry = kyc.id_expiry_date
            if isinstance(id_expiry, str):
                try: id_expiry = datetime.strptime(id_expiry, '%Y-%m-%d').date()
                except: pass
            if not isinstance(id_expiry, str) and id_expiry < valid_until.date():
                valid_until = datetime.combine(id_expiry, datetime.min.time())
        kyc.verification_valid_until = valid_until
        target_user.is_verified = True"""

    old_logic_2 = """        kyc.verification_status = "verified"
        target_user.is_verified = True"""

    # We use replace for safety
    if old_logic_1 in content:
        content = content.replace(old_logic_1, expiry_logic_1)
        print("Patched admin.py old_logic_1")
    
    if old_logic_2 in content:
        content = content.replace(old_logic_2, expiry_logic_2)
        print("Patched admin.py old_logic_2")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

add_expiry_admin()
