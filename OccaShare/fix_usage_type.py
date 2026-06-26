import re
with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "equipment_items = [e for e in profile.equipment_items if not e.is_archived and e.status == 'available']",
    "equipment_items = [e for e in profile.equipment_items if not e.is_archived and e.status == 'available' and getattr(e, 'usage_type', 'both') != 'order_only']"
)
content = content.replace(
    "service_items = [s for s in profile.service_items if not s.is_archived and s.status == 'available']",
    "service_items = [s for s in profile.service_items if not s.is_archived and s.status == 'available' and getattr(s, 'usage_type', 'both') != 'order_only']"
)
content = content.replace(
    "legacy_items = [m for m in profile.menu_items if not m.is_archived and m.status == 'available' and m.category in service_cats]",
    "legacy_items = [m for m in profile.menu_items if not m.is_archived and m.status == 'available' and m.category in service_cats and getattr(m, 'usage_type', 'both') != 'order_only']"
)

# And for active_menu (Dishes)
content = content.replace(
    "active_menu = [m for m in profile.menu_items if not m.is_archived and m.category not in service_cats]",
    "active_menu = [m for m in profile.menu_items if not m.is_archived and m.category not in service_cats and getattr(m, 'usage_type', 'both') != 'order_only']"
)

with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Filtered out order_only items!')
