import re

file_path = r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace get_all_menu_items_api
old_api = """@router.get("/api/menu")
async def get_all_menu_items_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        models.MenuItem.is_archived == False,
        models.MenuItem.available_for_package == True
    ).all()
    
    result = [
        {
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "image_url": i.image_url,
            "cost_price": i.cost_price,
            "price": i.price,
            "is_addon": i.is_addon
        }
        for i in items
    ]
    
    eqs = db.query(models.Equipment).filter(
        models.Equipment.caterer_id == user.caterer_profile.id,
        models.Equipment.is_hidden == False,
        models.Equipment.status == 'available'
    ).all()
    for e in eqs:
        result.append({
            "id": f"eq_{e.id}",
            "name": e.name,
            "category": e.category or 'Equipment',
            "image_url": e.image_url,
            "cost_price": e.cost_value,
            "price": e.rental_price,
            "is_addon": getattr(e, 'is_addon', False)
        })
        
    svcs = db.query(models.Service).filter(
        models.Service.caterer_id == user.caterer_profile.id,
        models.Service.is_archived == False,
        models.Service.status == 'available'
    ).all()
    for s in svcs:
        result.append({
            "id": f"svc_{s.id}",
            "name": s.name,
            "category": s.category or 'Service',
            "image_url": s.image_url,
            "cost_price": s.cost,
            "price": s.selling_price,
            "is_addon": getattr(s, 'is_addon', False)
        })
        
    return result"""

new_api = """@router.get("/api/menu")
async def get_all_menu_items_api(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    items = db.query(models.MenuItem).filter(
        models.MenuItem.caterer_id == user.caterer_profile.id,
        models.MenuItem.is_archived == False
    ).all()
    
    result = [
        {
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "image_url": i.image_url,
            "cost_price": i.cost_price,
            "price": i.price,
            "is_addon": i.is_addon
        }
        for i in items
    ]
    
    eqs = db.query(models.Equipment).filter(
        models.Equipment.caterer_id == user.caterer_profile.id,
        models.Equipment.is_archived == False
    ).all()
    for e in eqs:
        result.append({
            "id": f"eq_{e.id}",
            "name": e.name,
            "category": e.category or 'Equipment',
            "image_url": e.image_url,
            "cost_price": e.cost_value,
            "price": e.rental_price,
            "is_addon": getattr(e, 'is_addon', False)
        })
        
    svcs = db.query(models.Service).filter(
        models.Service.caterer_id == user.caterer_profile.id,
        models.Service.is_archived == False
    ).all()
    for s in svcs:
        result.append({
            "id": f"svc_{s.id}",
            "name": s.name,
            "category": s.category or 'Service',
            "image_url": s.image_url,
            "cost_price": s.cost,
            "price": s.selling_price,
            "is_addon": getattr(s, 'is_addon', False)
        })
        
    return result"""

if old_api in content:
    content = content.replace(old_api, new_api)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("API update complete.")
else:
    print("Could not find old API text to replace.")
