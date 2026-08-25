import re

with open("c:\\OccaServe\\OccaShare\\app\\routers\\caterer_dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

# We need to remove from @router.get("/compliance/view/{user_id}", response_class=HTMLResponse)
# down to the end of verify_customer_compliance route

# Pattern to find the start of the view_customer_verification route
start_pattern = r'@router\.get\("/compliance/view/\{user_id\}", response_class=HTMLResponse\)'
# Pattern to find the end of the verify_customer_compliance route (it ends right before "# --- SMART PRICING & QUICK BOOK SYSTEM ---")
end_pattern = r'# --- SMART PRICING & QUICK BOOK SYSTEM ---'

import sys
start_match = re.search(start_pattern, content)
end_match = re.search(end_pattern, content)

if start_match and end_match:
    new_content = content[:start_match.start()] + content[end_match.start():]
    with open("c:\\OccaServe\\OccaShare\\app\\routers\\caterer_dashboard.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully removed raw ID access routes from caterer_dashboard.")
else:
    print("Could not find the routes to remove.")
