import sys

with open(r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

old_str = "Duplicate Error: This customer already has an existing booking for a '{event_type}' on {event_date.strftime('%b %d, %Y')}. Duplicate entries are not allowed."
new_str = "Duplicate Error: The customer '{target_user.first_name}' already has an active booking registered on {event_date.strftime('%b %d, %Y')}. Double-booking the same customer on the exact same day is prohibited to prevent data redundancy."

content = content.replace(old_str, new_str)

with open(r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done!")
