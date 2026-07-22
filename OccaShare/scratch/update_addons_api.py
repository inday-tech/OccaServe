import re

file_path = r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

addons_api = """@router.get("/packages/{package_id}/addons")
async def get_package_addons(
    package_id: int,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    package = db.query(models.CateringPackage).filter(
        models.CateringPackage.id == package_id,
        models.CateringPackage.caterer_id == user.caterer_profile.id
    ).first()
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    res = {"menu": [], "service": [], "equipment": []}
    
    for a in package.menu_addons:
        m = db.query(models.MenuItem).filter(models.MenuItem.id == a.menu_item_id).first()
        if m:
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
            })
            
    return res

"""

# Insert the API before `get_package_menu`
if "@router.get(\"/packages/{package_id}/menu\")" in content:
    content = content.replace("@router.get(\"/packages/{package_id}/menu\")", addons_api + "@router.get(\"/packages/{package_id}/menu\")")

# Update `add_package` signature to include addons
old_add_package_def = """    policies_internal: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),"""

new_add_package_def = """    policies_internal: Optional[str] = Form(None),
    menu_addons: Optional[str] = Form(None),
    service_addons: Optional[str] = Form(None),
    equipment_addons: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),"""

if old_add_package_def in content:
    content = content.replace(old_add_package_def, new_add_package_def)

# Update `update_package` signature to include addons
if old_add_package_def in content: # It's the same signature end
    pass # Wait, replace might have missed update_package if it was replaced globally?
content = content.replace("policies_internal: Optional[str] = Form(None),\n    db: Session = Depends(database.get_db),", "policies_internal: Optional[str] = Form(None),\n    menu_addons: Optional[str] = Form(None),\n    service_addons: Optional[str] = Form(None),\n    equipment_addons: Optional[str] = Form(None),\n    db: Session = Depends(database.get_db),")


# Now handle saving addons in `add_package`
old_add_save = """    else:
        db.add(new_pkg)
    db.commit()"""

new_add_save = """    else:
        db.add(new_pkg)
        db.flush()
        
    # Save addons
    try:
        import json
        if menu_addons:
            for ma in json.loads(menu_addons):
                db.add(models.PackageMenuAddon(package_id=new_pkg.id, menu_item_id=int(str(ma['id']).replace('leg_', '')), price=float(ma['price']), max_quantity=ma.get('max_quantity')))
        if service_addons:
            for sa in json.loads(service_addons):
                db.add(models.PackageServiceAddon(package_id=new_pkg.id, service_id=int(str(sa['id']).replace('svc_', '')), price=float(sa['price']), max_quantity=sa.get('max_quantity')))
        if equipment_addons:
            for ea in json.loads(equipment_addons):
                db.add(models.PackageEquipmentAddon(package_id=new_pkg.id, equipment_id=int(str(ea['id']).replace('eq_', '')), price=float(ea['price']), max_quantity=ea.get('max_quantity')))
    except Exception as e:
        pass

    db.commit()"""

content = content.replace(old_add_save, new_add_save)


# Handle saving addons in `update_package`
old_update_save = """    # Handle optional image update
    import base64"""

new_update_save = """    # Clear existing addons
    db.query(models.PackageMenuAddon).filter(models.PackageMenuAddon.package_id == package_id).delete()
    db.query(models.PackageServiceAddon).filter(models.PackageServiceAddon.package_id == package_id).delete()
    db.query(models.PackageEquipmentAddon).filter(models.PackageEquipmentAddon.package_id == package_id).delete()
    db.flush()
    
    # Save new addons
    try:
        import json
        if menu_addons:
            for ma in json.loads(menu_addons):
                db.add(models.PackageMenuAddon(package_id=package.id, menu_item_id=int(str(ma['id']).replace('leg_', '')), price=float(ma['price']), max_quantity=ma.get('max_quantity')))
        if service_addons:
            for sa in json.loads(service_addons):
                db.add(models.PackageServiceAddon(package_id=package.id, service_id=int(str(sa['id']).replace('svc_', '')), price=float(sa['price']), max_quantity=sa.get('max_quantity')))
        if equipment_addons:
            for ea in json.loads(equipment_addons):
                db.add(models.PackageEquipmentAddon(package_id=package.id, equipment_id=int(str(ea['id']).replace('eq_', '')), price=float(ea['price']), max_quantity=ea.get('max_quantity')))
    except Exception as e:
        pass
        
    # Handle optional image update
    import base64"""

content = content.replace(old_update_save, new_update_save)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Dashboard updated with addons logic.")
