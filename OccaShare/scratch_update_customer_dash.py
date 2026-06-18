import re

filepath = 'c:/OccaServe/OccaShare/app/routers/customer_dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Filter active menu to ONLY show available and public items
pattern = r'active_menu = \[m for m in caterer\.menu_items if not m\.is_archived\]'
replacement = r"active_menu = [m for m in caterer.menu_items if not m.is_archived and not m.is_hidden and m.status == 'available' and m.category not in ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']]"
content = re.sub(pattern, replacement, content)

# I should also pass public equipment and services to the customer view if we want them to see it.
# Actually, the user asked earlier "bakit may tent pa naka display kay customer", meaning they probably don't want standalone inventory shown UNLESS we specifically design a section for it.
# For now, let's just make sure active_menu only contains food items, and they are public.

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated customer_dashboard.py")
