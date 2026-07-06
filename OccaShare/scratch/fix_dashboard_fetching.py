import codecs

file_path = 'c:\\OccaServe\\OccaShare\\app\\routers\\customer_dashboard.py'
with codecs.open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: active_menu logic missing usage_type check
old_menu = """    active_menu = [
        m for m in caterer.menu_items
        if not m.is_archived
        and not m.is_hidden
        and m.status == 'available'
        and m.category not in ['Rentals', 'Services', 'Event Styling', 'Event Rental',
                                'Entertainment', 'Event Coordination', 'Food Cart',
                                'Equipment Rental', 'Staffing Services', 'Packages']
    ]"""
new_menu = """    active_menu = [
        m for m in caterer.menu_items
        if not m.is_archived
        and not m.is_hidden
        and m.status == 'available'
        and m.category not in ['Rentals', 'Services', 'Event Styling', 'Event Rental',
                                'Entertainment', 'Event Coordination', 'Food Cart',
                                'Equipment Rental', 'Staffing Services', 'Packages']
        and getattr(m, 'usage_type', '') != 'package_only'
    ]"""
content = content.replace(old_menu, new_menu)

# Fix 2: active_services missing usage_type check
old_services = """    active_services = [
        s for s in getattr(caterer, 'service_items', [])
        if not s.is_archived and not s.is_hidden and s.status == 'available'
    ]"""
new_services = """    active_services = [
        s for s in getattr(caterer, 'service_items', [])
        if not s.is_archived and not s.is_hidden and s.status == 'available'
        and getattr(s, 'usage_type', '') != 'package_only'
    ]"""
content = content.replace(old_services, new_services)

# Fix 3: active_equipment missing usage_type check
old_equip = """    active_equipment = [
        e for e in getattr(caterer, 'equipment_items', [])
        if not e.is_archived and not e.is_hidden and e.status == 'available'
    ]"""
new_equip = """    active_equipment = [
        e for e in getattr(caterer, 'equipment_items', [])
        if not e.is_archived and not e.is_hidden and e.status == 'available'
        and getattr(e, 'usage_type', '') != 'package_only'
    ]"""
content = content.replace(old_equip, new_equip)

# Also adding a database refresh to ensure the data is fresh!
old_refresh = """    caterer = crud.get_caterer(db, caterer_id=caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")"""

new_refresh = """    caterer = crud.get_caterer(db, caterer_id=caterer_id)
    if not caterer:
        raise HTTPException(status_code=404, detail="Caterer not found")
    
    # Force refresh the object to prevent fetching old cached versions
    db.refresh(caterer)"""

content = content.replace(old_refresh, new_refresh)

with codecs.open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
