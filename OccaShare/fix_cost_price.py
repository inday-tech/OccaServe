import re
with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# For add_menu_item
old_add_extract = '''    try:
        addon_price = float(form_data.get("addon_price", "0").replace(",", ""))
    except ValueError:
        addon_price = 0.0'''
new_add_extract = '''    try:
        addon_price = float(form_data.get("addon_price", "0").replace(",", ""))
    except ValueError:
        addon_price = 0.0

    try:
        cost_price = float(str(form_data.get("cost_price", "0")).replace(",", ""))
    except ValueError:
        cost_price = 0.0'''
content = content.replace(old_add_extract, new_add_extract, 1)

old_add_inst = '''    new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        price=price,'''
new_add_inst = '''    new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        cost_price=cost_price,
        price=price,'''
content = content.replace(old_add_inst, new_add_inst, 1)

# For update_menu_item
old_upd_extract = '''    try:
        addon_price = float(form_data.get("addon_price", "0").replace(",", ""))
    except ValueError:
        addon_price = 0.0'''
new_upd_extract = '''    try:
        addon_price = float(form_data.get("addon_price", "0").replace(",", ""))
    except ValueError:
        addon_price = 0.0

    try:
        cost_price = float(str(form_data.get("cost_price", "0")).replace(",", ""))
    except ValueError:
        cost_price = 0.0'''
content = content.replace(old_upd_extract, new_upd_extract, 1) # Only replaces the first occurrence after the previous one, assuming they are in order.
# Wait, replace(old, new, 1) will just replace the next one it finds from the start of the string!
# Let's just do a global replace for extract since it's the same pattern!
