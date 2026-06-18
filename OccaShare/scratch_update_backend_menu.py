import re

filepath = 'c:/OccaServe/OccaShare/app/routers/caterer_dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern for add_menu_item
add_pattern = r'@router\.post\("/menu/add"\)\nasync def add_menu_item\(.*?\n    return RedirectResponse\(url="/caterer/menu\?success_msg=Menu\+item\+added\+successfully", status_code=303\)'
add_replacement = """@router.post("/menu/add")
async def add_menu_item(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    cost_price: float = Form(0.0),
    unit_type: str = Form("Per Pax"),
    is_hidden: bool = Form(False),
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

    new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        price=price,
        cost_price=cost_price,
        pricing_unit=unit_type,
        is_hidden=is_hidden,
        image_url=image_url,
        is_archived=False
    )
    db.add(new_item)
    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "status": "success", 
            "message": "Dish added successfully", 
            "item_id": new_item.id,
            "item_name": new_item.name
        })

    return RedirectResponse(url="/caterer/menu?success_msg=Dish+added+successfully", status_code=303)"""

# Pattern for update_menu_item
update_pattern = r'@router\.post\("/menu/\{item_id\}/update"\)\nasync def update_menu_item\(.*?\n    return RedirectResponse\(url="/caterer/menu\?success_msg=Menu\+item\+updated\+successfully", status_code=303\)'
update_replacement = """@router.post("/menu/{item_id}/update")
async def update_menu_item(
    item_id: int,
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(0.0),
    cost_price: float = Form(0.0),
    unit_type: str = Form("Per Pax"),
    is_hidden: bool = Form(False),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    import base64
    item = db.query(models.MenuItem).get(item_id)
    if not item or item.caterer_id != user.caterer_profile.id:
        raise HTTPException(status_code=404, detail="Item not found")

    item.name = name
    item.category = category
    item.description = description
    item.price = price
    item.cost_price = cost_price
    item.pricing_unit = unit_type
    item.is_hidden = is_hidden

    if image and image.filename:
        try:
            content_bytes = await image.read()
            if content_bytes:
                encoded = base64.b64encode(content_bytes).decode("utf-8")
                mime = image.content_type or "image/jpeg"
                item.image_url = f"data:{mime};base64,{encoded}"
        except Exception:
            pass

    db.commit()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({"status": "success", "message": "Dish updated successfully"})

    return RedirectResponse(url="/caterer/menu?success_msg=Dish+updated+successfully", status_code=303)"""

content = re.sub(add_pattern, add_replacement, content, flags=re.DOTALL)
content = re.sub(update_pattern, update_replacement, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated backend routes")
