import re
with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix equipment_items
old_eq = "equipment_items = [e for e in profile.equipment_items if not e.is_archived and e.status == 'available' and getattr(e, 'usage_type', 'both') != 'order_only']"
new_eq = "equipment_items = [e for e in profile.equipment_items if not e.is_archived and e.status == 'available' and (getattr(e, 'usage_type', 'both') != 'order_only' or getattr(e, 'is_addon', False))]"
content = content.replace(old_eq, new_eq)

# Fix service_items
old_sv = "service_items = [s for s in profile.service_items if not s.is_archived and s.status == 'available' and getattr(s, 'usage_type', 'both') != 'order_only']"
new_sv = "service_items = [s for s in profile.service_items if not s.is_archived and s.status == 'available' and (getattr(s, 'usage_type', 'both') != 'order_only' or getattr(s, 'is_addon', False))]"
content = content.replace(old_sv, new_sv)

# Fix legacy_items
old_lg = "legacy_items = [m for m in profile.menu_items if not m.is_archived and m.status == 'available' and m.category in service_cats and getattr(m, 'usage_type', 'both') != 'order_only']"
new_lg = "legacy_items = [m for m in profile.menu_items if not m.is_archived and m.status == 'available' and m.category in service_cats and (getattr(m, 'usage_type', 'both') != 'order_only' or getattr(m, 'is_addon', False))]"
content = content.replace(old_lg, new_lg)

# Fix active_menu
old_menu = "active_menu = [m for m in profile.menu_items if not m.is_archived and m.category not in service_cats and getattr(m, 'usage_type', 'both') != 'order_only']"
new_menu = "active_menu = [m for m in profile.menu_items if not m.is_archived and m.category not in service_cats and (getattr(m, 'usage_type', 'both') != 'order_only' or getattr(m, 'is_addon', False))]"
content = content.replace(old_menu, new_menu)

with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed manage_packages logic!')
