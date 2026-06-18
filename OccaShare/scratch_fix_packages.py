import re

filepath = 'c:/OccaServe/OccaShare/app/routers/caterer_dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix add_package signature
content = content.replace(
    'linked_menu_ids: Optional[List[int]] = Form(None),',
    'linked_menu_ids: Optional[List[str]] = Form(None),'
)

# 2. Fix add_package logic
old_add_logic = """    # Handle linked menu items via separate PackageDish and PackageService tables
    if linked_menu_ids:
        items = db.query(models.MenuItem).filter(
            models.MenuItem.id.in_(linked_menu_ids),
            models.MenuItem.caterer_id == user.caterer_profile.id
        ).all()
        # For backward compatibility, keep generic junction
        new_pkg.menu_items = items
        
        # Flush to get new_pkg.id
        db.add(new_pkg)
        db.flush()
        
        # Insert into specific tables
        service_categories = ['rentals', 'services', 'equipment']
        for item in items:
            cat = item.category.lower() if item.category else ''
            if cat in service_categories:
                new_service = models.PackageService(package_id=new_pkg.id, service_id=item.id, quantity=1)
                db.add(new_service)
            else:
                new_dish = models.PackageDish(package_id=new_pkg.id, menu_item_id=item.id, category_assigned=item.category)
                db.add(new_dish)"""

new_add_logic = """    # Handle linked items
    if linked_menu_ids:
        db.add(new_pkg)
        db.flush()
        
        menu_ids = []
        eq_ids = []
        svc_ids = []
        for i in set(linked_menu_ids):
            if i.startswith('eq_'): eq_ids.append(int(i.replace('eq_', '')))
            elif i.startswith('svc_'): svc_ids.append(int(i.replace('svc_', '')))
            elif i.startswith('leg_'): menu_ids.append(int(i.replace('leg_', '')))
            else:
                try: menu_ids.append(int(i))
                except: pass
                
        if menu_ids:
            items = db.query(models.MenuItem).filter(models.MenuItem.id.in_(menu_ids)).all()
            new_pkg.menu_items = items
            
        if eq_ids:
            for eid in eq_ids:
                db.add(models.PackageEquipment(package_id=new_pkg.id, equipment_id=eid, quantity=1))
                
        if svc_ids:
            for sid in svc_ids:
                db.add(models.PackageService(package_id=new_pkg.id, service_id=sid, quantity=1))"""

content = content.replace(old_add_logic, new_add_logic)

# 3. Fix update_package logic
old_update_logic = """    if linked_menu_ids:
        # Clear existing
        package.menu_items = []
        # Add new
        for mid in set(linked_menu_ids):
            item = db.query(models.MenuItem).get(mid)
            if item and item.caterer_id == user.caterer_profile.id:
                package.menu_items.append(item)"""

new_update_logic = """    if linked_menu_ids is not None:
        menu_ids = []
        eq_ids = []
        svc_ids = []
        for i in set(linked_menu_ids):
            if i.startswith('eq_'): eq_ids.append(int(i.replace('eq_', '')))
            elif i.startswith('svc_'): svc_ids.append(int(i.replace('svc_', '')))
            elif i.startswith('leg_'): menu_ids.append(int(i.replace('leg_', '')))
            else:
                try: menu_ids.append(int(i))
                except: pass

        # Clear existing
        package.menu_items = []
        db.query(models.PackageEquipment).filter(models.PackageEquipment.package_id == package.id).delete()
        db.query(models.PackageService).filter(models.PackageService.package_id == package.id).delete()
        
        # Add new
        if menu_ids:
            items = db.query(models.MenuItem).filter(models.MenuItem.id.in_(menu_ids)).all()
            package.menu_items = items
            
        for eid in eq_ids:
            db.add(models.PackageEquipment(package_id=package.id, equipment_id=eid, quantity=1))
        for sid in svc_ids:
            db.add(models.PackageService(package_id=package.id, service_id=sid, quantity=1))"""

content = content.replace(old_update_logic, new_update_logic)

# 4. Fix get_package_menu
old_get_menu = """@router.get("/packages/{package_id}/menu")
async def get_package_menu(
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
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "image_url": item.image_url,
            "is_addon": item.is_addon
        }
        for item in package.menu_items
    ]"""

new_get_menu = """@router.get("/packages/{package_id}/menu")
async def get_package_menu(
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
    
    res = [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "image_url": item.image_url,
            "is_addon": item.is_addon
        }
        for item in package.menu_items
    ]
    
    eqs = db.query(models.PackageEquipment).filter(models.PackageEquipment.package_id == package.id).all()
    for e in eqs:
        res.append({"id": f"eq_{e.equipment_id}"})
        
    svcs = db.query(models.PackageService).filter(models.PackageService.package_id == package.id).all()
    for s in svcs:
        res.append({"id": f"svc_{s.service_id}"})
        
    return res"""

content = content.replace(old_get_menu, new_get_menu)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS")
