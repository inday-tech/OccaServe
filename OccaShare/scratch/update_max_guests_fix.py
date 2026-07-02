import re

f = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

# Replace add_package definition
old_add_def = """    min_guests: int = Form(50),
    max_guests: Optional[int] = Form(None),
    booking_lead_time: int = Form(7),"""
new_add_def = """    min_guests: int = Form(50),
    max_guests: Optional[str] = Form(None),
    booking_lead_time: int = Form(7),"""
content = content.replace(old_add_def, new_add_def)

# Cast max_guests in add_package
old_add_body = """    if min_guests < 1:
        raise HTTPException(status_code=400, detail="Minimum guests must be at least 1")"""
new_add_body = """    max_guests = int(max_guests) if max_guests and str(max_guests).strip() else None
    if min_guests < 1:
        raise HTTPException(status_code=400, detail="Minimum guests must be at least 1")"""
content = content.replace(old_add_body, new_add_body)

# Replace update_package definition
old_upd_def = """    min_guests: int = Form(50),
    max_guests: Optional[int] = Form(None),
    booking_lead_time: int = Form(7),"""
# Note: since the string is the same, this will be handled automatically if we do replace multiple times, but I used string replacement on the first block. Let's do it globally.
content = content.replace(old_upd_def, new_add_def)

# Cast max_guests in update_package
old_upd_body = """    if min_guests < 1:
        raise HTTPException(status_code=400, detail="Minimum guests must be at least 1")"""
# Since it's the exact same string, it replaces both. Let's make sure.
content = content.replace(old_upd_body, new_add_body)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Updated caterer_dashboard.py')
