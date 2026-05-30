import re

def update_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for search_str, type_val in replacements:
        # We need to find the models.Notification block that contains the search_str
        # and insert 	ype="...", after message=...,
        # Because regex across multiple lines is tricky, we'll replace manually
        
        # Find index of search_str
        idx = content.find(search_str)
        if idx != -1:
            # Find the next )
            end_idx = content.find(')', idx)
            block = content[idx:end_idx]
            if 'type=' not in block:
                # find the last , before end_idx
                last_comma = content.rfind(',', idx, end_idx)
                if last_comma != -1:
                    content = content[:last_comma+1] + f'\n        type="{type_val}",' + content[last_comma+1:]
                    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

update_file(r'c:\OccaServe\OccaShare\app\routers\customer_dashboard.py', [
    ('title="Payment Submitted"', 'Payment')
])

update_file(r'c:\OccaServe\OccaShare\app\routers\admin.py', [
    ('title="Administrative Alert"', 'Verification'),
    ('title=f"Administrative Alert: Booking #BK-{booking_id}"', 'Booking')
])

update_file(r'c:\OccaServe\OccaShare\app\routers\auth.py', [
    ('title="New Caterer Application"', 'Verification')
])

update_file(r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', [
    ('title=f"Reminder: {booking.event_name or \'Event\'}"', 'Booking'),
    ('title="Commission Settlement Pending"', 'Payment')
])
