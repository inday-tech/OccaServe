import re

f = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

# Update get_package_addons
old_get = """        if m:
            res["menu"].append({
                "id": m.id,
                "name": m.name,
                "price": a.price,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })
            
    for a in package.service_addons:
        s = db.query(models.Service).filter(models.Service.id == a.service_id).first()
        if s:
            res["service"].append({
                "id": f"svc_{s.id}",
                "name": s.name,
                "price": a.price,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })
            
    for a in package.equipment_addons:
        e = db.query(models.Equipment).filter(models.Equipment.id == a.equipment_id).first()
        if e:
            res["equipment"].append({
                "id": f"eq_{e.id}",
                "name": e.name,
                "price": a.price,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })"""

new_get = """        if m:
            res["menu"].append({
                "id": m.id,
                "name": m.name,
                "price": a.price,
                "selection_type": a.selection_type,
                "min_quantity": a.min_quantity,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })
            
    for a in package.service_addons:
        s = db.query(models.Service).filter(models.Service.id == a.service_id).first()
        if s:
            res["service"].append({
                "id": f"svc_{s.id}",
                "name": s.name,
                "price": a.price,
                "selection_type": a.selection_type,
                "min_quantity": a.min_quantity,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })
            
    for a in package.equipment_addons:
        e = db.query(models.Equipment).filter(models.Equipment.id == a.equipment_id).first()
        if e:
            res["equipment"].append({
                "id": f"eq_{e.id}",
                "name": e.name,
                "price": a.price,
                "min_quantity": a.min_quantity,
                "max_quantity": a.max_quantity,
                "is_enabled": a.is_enabled
            })"""
content = content.replace(old_get, new_get)

# Update add_package
old_add_save = """        if menu_addons:
            for ma in json.loads(menu_addons):
                db.add(models.PackageMenuAddon(package_id=new_pkg.id, menu_item_id=int(str(ma['id']).replace('leg_', '')), price=float(ma['price']), max_quantity=ma.get('max_quantity')))
        if service_addons:
            for sa in json.loads(service_addons):
                db.add(models.PackageServiceAddon(package_id=new_pkg.id, service_id=int(str(sa['id']).replace('svc_', '')), price=float(sa['price']), max_quantity=sa.get('max_quantity')))
        if equipment_addons:
            for ea in json.loads(equipment_addons):
                db.add(models.PackageEquipmentAddon(package_id=new_pkg.id, equipment_id=int(str(ea['id']).replace('eq_', '')), price=float(ea['price']), max_quantity=ea.get('max_quantity')))"""

new_add_save = """        if menu_addons:
            for ma in json.loads(menu_addons):
                db.add(models.PackageMenuAddon(package_id=new_pkg.id, menu_item_id=int(str(ma['id']).replace('leg_', '')), price=float(ma['price']), selection_type=ma.get('selection_type', 'single'), min_quantity=ma.get('min_quantity', 1), max_quantity=ma.get('max_quantity')))
        if service_addons:
            for sa in json.loads(service_addons):
                db.add(models.PackageServiceAddon(package_id=new_pkg.id, service_id=int(str(sa['id']).replace('svc_', '')), price=float(sa['price']), selection_type=ma.get('selection_type', 'single'), min_quantity=sa.get('min_quantity', 1), max_quantity=sa.get('max_quantity')))
        if equipment_addons:
            for ea in json.loads(equipment_addons):
                db.add(models.PackageEquipmentAddon(package_id=new_pkg.id, equipment_id=int(str(ea['id']).replace('eq_', '')), price=float(ea['price']), min_quantity=ea.get('min_quantity', 1), max_quantity=ea.get('max_quantity')))"""
content = content.replace(old_add_save, new_add_save)

# Update update_package
old_upd_save = """        if menu_addons:
            for ma in json.loads(menu_addons):
                db.add(models.PackageMenuAddon(package_id=package.id, menu_item_id=int(str(ma['id']).replace('leg_', '')), price=float(ma['price']), max_quantity=ma.get('max_quantity')))
        if service_addons:
            for sa in json.loads(service_addons):
                db.add(models.PackageServiceAddon(package_id=package.id, service_id=int(str(sa['id']).replace('svc_', '')), price=float(sa['price']), max_quantity=sa.get('max_quantity')))
        if equipment_addons:
            for ea in json.loads(equipment_addons):
                db.add(models.PackageEquipmentAddon(package_id=package.id, equipment_id=int(str(ea['id']).replace('eq_', '')), price=float(ea['price']), max_quantity=ea.get('max_quantity')))"""

new_upd_save = """        if menu_addons:
            for ma in json.loads(menu_addons):
                db.add(models.PackageMenuAddon(package_id=package.id, menu_item_id=int(str(ma['id']).replace('leg_', '')), price=float(ma['price']), selection_type=ma.get('selection_type', 'single'), min_quantity=ma.get('min_quantity', 1), max_quantity=ma.get('max_quantity')))
        if service_addons:
            for sa in json.loads(service_addons):
                db.add(models.PackageServiceAddon(package_id=package.id, service_id=int(str(sa['id']).replace('svc_', '')), price=float(sa['price']), selection_type=sa.get('selection_type', 'single'), min_quantity=sa.get('min_quantity', 1), max_quantity=sa.get('max_quantity')))
        if equipment_addons:
            for ea in json.loads(equipment_addons):
                db.add(models.PackageEquipmentAddon(package_id=package.id, equipment_id=int(str(ea['id']).replace('eq_', '')), price=float(ea['price']), min_quantity=ea.get('min_quantity', 1), max_quantity=ea.get('max_quantity')))"""
content = content.replace(old_upd_save, new_upd_save)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Updated caterer_dashboard.py')
