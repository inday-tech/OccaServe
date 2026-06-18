import re

filepath = 'c:/OccaServe/OccaShare/app/routers/caterer_dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace manage_services route
manage_services_pattern = r'@router\.get\("/services".*?return templates\.TemplateResponse\("caterer/services\.html", \{\n\s+"request": request,\n\s+"user": user,\n\s+"items": items,\n\s+"active_page": "services"\n\s+\}\)'
manage_services_replacement = """@router.get("/services", response_class=HTMLResponse)
async def manage_services(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    equipment_items = [e for e in user.caterer_profile.equipment_items if not e.is_archived]
    service_items = [s for s in user.caterer_profile.service_items if not s.is_archived]
    
    # Legacy items in menu_items table
    service_cats = ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']
    legacy_items = [m for m in user.caterer_profile.menu_items if not m.is_archived and m.category in service_cats]
    
    # Unify them for the frontend
    items = []
    for e in equipment_items:
        items.append({
            "id": e.id,
            "item_type": e.equipment_type or "Equipment",
            "name": e.name,
            "category": e.category,
            "description": e.description,
            "price": e.rental_price,
            "cost_price": e.cost_value,
            "unit_type": e.unit_type,
            "available_qty": e.available_qty,
            "status": e.status,
            "image_url": e.image_url
        })
    for s in service_items:
        items.append({
            "id": s.id,
            "item_type": "Service",
            "name": s.name,
            "category": s.category,
            "description": s.description,
            "price": s.selling_price,
            "cost_price": s.cost,
            "unit_type": s.unit_type,
            "available_qty": s.max_available,
            "status": s.status,
            "image_url": s.image_url
        })
    for m in legacy_items:
        items.append({
            "id": m.id,
            "item_type": "Legacy",
            "name": m.name,
            "category": m.category,
            "description": m.description,
            "price": m.price,
            "cost_price": m.cost_price,
            "unit_type": m.pricing_unit,
            "available_qty": m.max_stock_quantity or 1,
            "status": "unavailable" if m.is_hidden else "available",
            "image_url": m.image_url
        })

    return templates.TemplateResponse("caterer/services.html", {
        "request": request,
        "user": user,
        "items": items,
        "active_page": "services"
    })"""

archive_service_pattern = r'@router\.post\("/services/\{item_id\}/archive"\)\nasync def archive_service_item\(.*?\n    return RedirectResponse\(url="/caterer/services", status_code=303\)'
archive_service_replacement = """@router.post("/services/{item_id}/archive")
async def archive_service_item(
    item_id: int,
    type: str,
    request: Request,
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    if type in ["Equipment", "Decoration"]:
        item = db.query(models.Equipment).get(item_id)
    elif type == "Legacy":
        item = db.query(models.MenuItem).get(item_id)
    else:
        item = db.query(models.Service).get(item_id)
        
    if not item or item.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Item not found")
        
    item.is_archived = True
    db.commit()
    
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Item archived successfully"})
    return RedirectResponse(url="/caterer/services", status_code=303)"""

update_service_pattern = r'@router\.post\("/services/\{item_id\}/update"\)\nasync def update_service_item\(.*?\n    return RedirectResponse\(url="/caterer/services", status_code=303\)'
update_service_replacement = """@router.post("/services/{item_id}/update")
async def update_service_item(
    item_id: int,
    request: Request,
    type: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    cost_price: float = Form(0.0),
    unit_type: str = Form("Per Event"),
    available_qty: int = Form(1),
    status: str = Form("available"),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    import base64
    image_url = None
    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                encoded = base64.b64encode(content_bytes).decode("utf-8")
                mime = image.content_type or "image/jpeg"
                image_url = f"data:{mime};base64,{encoded}"
        except Exception:
            pass

    if type in ["Equipment", "Decoration"]:
        item = db.query(models.Equipment).get(item_id)
        if not item or item.caterer_id != user.caterer_profile.id:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = name
        item.category = category
        item.description = description
        item.rental_price = price
        item.cost_value = cost_price
        item.unit_type = unit_type
        item.available_qty = available_qty
        item.status = status
        if image_url: item.image_url = image_url
    elif type == "Legacy":
        item = db.query(models.MenuItem).get(item_id)
        if not item or item.caterer_id != user.caterer_profile.id:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = name
        item.category = category
        item.description = description
        item.price = price
        item.cost_price = cost_price
        item.pricing_unit = unit_type
        item.max_stock_quantity = available_qty
        item.is_hidden = (status == "unavailable")
        if image_url: item.image_url = image_url
    else:
        item = db.query(models.Service).get(item_id)
        if not item or item.caterer_id != user.caterer_profile.id:
            raise HTTPException(status_code=404, detail="Item not found")
        item.name = name
        item.category = category
        item.description = description
        item.selling_price = price
        item.cost = cost_price
        item.unit_type = unit_type
        item.max_available = available_qty
        item.status = status
        if image_url: item.image_url = image_url

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Item updated successfully"})
    return RedirectResponse(url="/caterer/services", status_code=303)"""

content = re.sub(manage_services_pattern, manage_services_replacement, content, flags=re.DOTALL)
content = re.sub(archive_service_pattern, archive_service_replacement, content, flags=re.DOTALL)
content = re.sub(update_service_pattern, update_service_replacement, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Merged legacy services into services logic.")
