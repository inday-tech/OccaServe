import sys

with open(r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    ('detail="Security Violation: You cannot create a booking using your own caterer email or contact number."', 'detail="manCustEmail|Security Violation: You cannot create a booking using your own caterer email or contact number."'),
    ('detail="First name and Last name are required"', 'detail="manFirstName|First name and Last name are required"'),
    ('detail="Invalid name format: First, middle, and last names cannot be identical."', 'detail="manLastName|Invalid name format: First, middle, and last names cannot be identical."'),
    ('detail="Complete address (Province, Municipality, Barangay) is required"', 'detail="manProvince|Complete address (Province, Municipality, Barangay) is required"'),
    ('detail="For security and reliability, only Gmail accounts are supported for customer records."', 'detail="manCustEmail|For security and reliability, only Gmail accounts are supported for customer records."'),
    ('detail="Invalid contact number. Must be a valid 11-digit PH mobile number (09xx)."', 'detail="manCustContact|Invalid contact number. Must be a valid 11-digit PH mobile number (09xx)."'),
    ('detail="Invalid contact number pattern detected. Please use a real mobile number."', 'detail="manCustContact|Invalid contact number pattern detected. Please use a real mobile number."'),
    ('detail="Event date is required."', 'detail="manDate|Event date is required."'),
    ('detail="Bookings must be made at least 2 days in advance. Bookings for today or tomorrow are not allowed."', 'detail="manDate|Bookings must be made at least 2 days in advance. Bookings for today or tomorrow are not allowed."'),
    ('detail=f"Duplicate Error: The customer \'{target_user.first_name}\' already has an active booking registered on {event_date.strftime(\'%b %d, %Y\')}. Double-booking the same customer on the exact same day is prohibited to prevent data redundancy."', 'detail=f"manDate|Duplicate Error: The customer \'{target_user.first_name}\' already has an active booking registered on {event_date.strftime(\'%b %d, %Y\')}. Double-booking the same customer on the exact same day is prohibited to prevent data redundancy."'),
    ('detail=f"The selected package \'{package.name}\' requires a minimum of {min_guests} guests."', 'detail=f"manGuests|The selected package \'{package.name}\' requires a minimum of {min_guests} guests."'),
    ('detail=f"This date is manually blocked: {manual_block.reason or \'No reason provided\'}. Unblock it first before adding bookings."', 'detail=f"manDate|This date is manually blocked: {manual_block.reason or \'No reason provided\'}. Unblock it first before adding bookings."'),
    ('detail=f"Capacity Reached: You already have {existing_on_date}/{max_cap} active bookings on {event_date}. You can override this by confirming in the capacity warning dialog."', 'detail=f"manDate|Capacity Reached: You already have {existing_on_date}/{max_cap} active bookings on {event_date}. You can override this by confirming in the capacity warning dialog."')
]

for old, new in replacements:
    content = content.replace(old, new)

with open(r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done replacing backend messages!")
