import re
with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace extraction logic for both
old_extract = '''    try:
        addon_price = float(form_data.get("addon_price", "0").replace(",", ""))
    except ValueError:
        addon_price = 0.0'''
new_extract = '''    try:
        addon_price = float(str(form_data.get("addon_price", "0")).replace(",", ""))
    except ValueError:
        addon_price = 0.0

    try:
        cost_price = float(str(form_data.get("cost_price", "0")).replace(",", ""))
    except ValueError:
        cost_price = 0.0'''
content = content.replace(old_extract, new_extract)

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
content = content.replace(old_add_inst, new_add_inst)

old_upd_inst = '''    item.name = name
    item.category = category
    item.description = description
    item.price = price'''
new_upd_inst = '''    item.name = name
    item.category = category
    item.description = description
    item.cost_price = cost_price
    item.price = price'''
content = content.replace(old_upd_inst, new_upd_inst)

with open(r'C:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done patching caterer_dashboard.py!')
