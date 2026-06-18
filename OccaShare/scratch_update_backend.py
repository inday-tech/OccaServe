import re

filepath = 'c:/OccaServe/OccaShare/app/routers/caterer_dashboard.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# For Menu Add:
# Find: async def add_menu_item( ... user: models.User = Depends(caterer_only) ):
menu_add_sig = r'(@router\.post\("/menu/add"\)\s*async def add_menu_item\(\s*request: Request,\s*name: str = Form\(\.\.\.\),\s*category: str = Form\(\.\.\.\),\s*description: Optional\[str\] = Form\(None\),\s*cost_price: float = Form\(\.\.\.\),\s*price: float = Form\(\.\.\.\),\s*unit_type: str = Form\(\.\.\.\),\s*status: str = Form\("available"\),\s*image: Optional\[UploadFile\] = File\(None\),\s*db: Session = Depends\(database\.get_db\),\s*user: models\.User = Depends\(caterer_only\)\s*\):)'

menu_add_rep = """@router.post("/menu/add")
async def add_menu_item(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    cost_price: float = Form(...),
    price: float = Form(...),
    unit_type: str = Form(...),
    status: str = Form("available"),
    visibility: str = Form("public"),
    dietary_tags: list = Form([]),
    allergen_info: list = Form([]),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):"""
content = re.sub(menu_add_sig, menu_add_rep, content)

menu_add_body = r'(new_item = models\.MenuItem\(\s*caterer_id=user\.caterer_profile\.id,\s*name=name,\s*category=category,\s*description=description,\s*cost_price=cost_price,\s*price=price,\s*pricing_unit=unit_type,\s*status=status,\s*image_url=image_url\s*\))'
menu_add_body_rep = """new_item = models.MenuItem(
        caterer_id=user.caterer_profile.id,
        name=name,
        category=category,
        description=description,
        cost_price=cost_price,
        price=price,
        pricing_unit=unit_type,
        status=status,
        is_hidden=(visibility == "hidden"),
        dietary_tags=dietary_tags,
        allergen_info=allergen_info,
        image_url=image_url
    )"""
content = re.sub(menu_add_body, menu_add_body_rep, content)


# For Menu Update:
menu_upd_sig = r'(@router\.post\("/menu/\{item_id\}/update"\)\s*async def update_menu_item\(\s*item_id: int,\s*request: Request,\s*name: str = Form\(\.\.\.\),\s*category: str = Form\(\.\.\.\),\s*description: Optional\[str\] = Form\(None\),\s*cost_price: float = Form\(\.\.\.\),\s*price: float = Form\(\.\.\.\),\s*unit_type: str = Form\(\.\.\.\),\s*status: str = Form\("available"\),\s*image: Optional\[UploadFile\] = File\(None\),\s*db: Session = Depends\(database\.get_db\),\s*user: models\.User = Depends\(caterer_only\)\s*\):)'
menu_upd_rep = """@router.post("/menu/{item_id}/update")
async def update_menu_item(
    item_id: int,
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    cost_price: float = Form(...),
    price: float = Form(...),
    unit_type: str = Form(...),
    status: str = Form("available"),
    visibility: str = Form("public"),
    dietary_tags: list = Form([]),
    allergen_info: list = Form([]),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):"""
content = re.sub(menu_upd_sig, menu_upd_rep, content)

menu_upd_body = r'(item\.name = name\s*item\.category = category\s*item\.description = description\s*item\.cost_price = cost_price\s*item\.price = price\s*item\.pricing_unit = unit_type\s*item\.status = status)'
menu_upd_body_rep = """item.name = name
    item.category = category
    item.description = description
    item.cost_price = cost_price
    item.price = price
    item.pricing_unit = unit_type
    item.status = status
    item.is_hidden = (visibility == "hidden")
    item.dietary_tags = dietary_tags
    item.allergen_info = allergen_info"""
content = re.sub(menu_upd_body, menu_upd_body_rep, content)


# For Service Add:
serv_add_sig = r'(@router\.post\("/services/add"\)\s*async def add_service_item\(\s*request: Request,\s*type: str = Form\(\.\.\.\),\s*name: str = Form\(\.\.\.\),\s*category: str = Form\(\.\.\.\),\s*description: Optional\[str\] = Form\(None\),\s*price: float = Form\(0\.0\),\s*cost_price: float = Form\(0\.0\),\s*unit_type: str = Form\("Per Event"\),\s*available_qty: int = Form\(1\),\s*status: str = Form\("available"\),\s*image: Optional\[UploadFile\] = File\(None\),\s*db: Session = Depends\(database\.get_db\),\s*user: models\.User = Depends\(caterer_only\)\s*\):)'
serv_add_rep = """@router.post("/services/add")
async def add_service_item(
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
    visibility: str = Form("public"),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):"""
content = re.sub(serv_add_sig, serv_add_rep, content)

serv_add_body1 = r'(new_item = models\.Equipment\(\s*caterer_id=user\.caterer_profile\.id,\s*equipment_type=type,\s*name=name,\s*category=category,\s*description=description,\s*rental_price=price,\s*cost_value=cost_price,\s*unit_type=unit_type,\s*available_qty=available_qty,\s*status=status,\s*image_url=image_url\s*\))'
serv_add_body1_rep = """new_item = models.Equipment(
            caterer_id=user.caterer_profile.id,
            equipment_type=type,
            name=name,
            category=category,
            description=description,
            rental_price=price,
            cost_value=cost_price,
            unit_type=unit_type,
            available_qty=available_qty,
            status=status,
            is_hidden=(visibility == "hidden"),
            image_url=image_url
        )"""
content = re.sub(serv_add_body1, serv_add_body1_rep, content)

serv_add_body2 = r'(new_item = models\.Service\(\s*caterer_id=user\.caterer_profile\.id,\s*name=name,\s*category=category,\s*description=description,\s*selling_price=price,\s*cost=cost_price,\s*unit_type=unit_type,\s*max_available=available_qty,\s*status=status,\s*image_url=image_url\s*\))'
serv_add_body2_rep = """new_item = models.Service(
            caterer_id=user.caterer_profile.id,
            name=name,
            category=category,
            description=description,
            selling_price=price,
            cost=cost_price,
            unit_type=unit_type,
            max_available=available_qty,
            status=status,
            is_hidden=(visibility == "hidden"),
            image_url=image_url
        )"""
content = re.sub(serv_add_body2, serv_add_body2_rep, content)


# For Service Update:
serv_upd_sig = r'(@router\.post\("/services/\{item_id\}/update"\)\s*async def update_service_item\(\s*item_id: int,\s*request: Request,\s*type: str = Form\(\.\.\.\),\s*name: str = Form\(\.\.\.\),\s*category: str = Form\(\.\.\.\),\s*description: Optional\[str\] = Form\(None\),\s*price: float = Form\(0\.0\),\s*cost_price: float = Form\(0\.0\),\s*unit_type: str = Form\("Per Event"\),\s*available_qty: int = Form\(1\),\s*status: str = Form\("available"\),\s*image: Optional\[UploadFile\] = File\(None\),\s*db: Session = Depends\(database\.get_db\),\s*user: models\.User = Depends\(caterer_only\)\s*\):)'
serv_upd_rep = """@router.post("/services/{item_id}/update")
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
    visibility: str = Form("public"),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):"""
content = re.sub(serv_upd_sig, serv_upd_rep, content)

serv_upd_body1 = r'(item\.name = name\s*item\.category = category\s*item\.description = description\s*item\.rental_price = price\s*item\.cost_value = cost_price\s*item\.unit_type = unit_type\s*item\.available_qty = available_qty\s*item\.status = status)'
serv_upd_body1_rep = """item.name = name
        item.category = category
        item.description = description
        item.rental_price = price
        item.cost_value = cost_price
        item.unit_type = unit_type
        item.available_qty = available_qty
        item.status = status
        item.is_hidden = (visibility == "hidden")"""
content = re.sub(serv_upd_body1, serv_upd_body1_rep, content)

serv_upd_body2 = r'(item\.name = name\s*item\.category = category\s*item\.description = description\s*item\.price = price\s*item\.cost_price = cost_price\s*item\.pricing_unit = unit_type\s*item\.max_stock_quantity = available_qty\s*item\.is_hidden = \(status == "unavailable"\))'
serv_upd_body2_rep = """item.name = name
        item.category = category
        item.description = description
        item.price = price
        item.cost_price = cost_price
        item.pricing_unit = unit_type
        item.max_stock_quantity = available_qty
        item.is_hidden = (visibility == "hidden")
        item.status = status"""
content = re.sub(serv_upd_body2, serv_upd_body2_rep, content)

serv_upd_body3 = r'(item\.name = name\s*item\.category = category\s*item\.description = description\s*item\.selling_price = price\s*item\.cost = cost_price\s*item\.unit_type = unit_type\s*item\.max_available = available_qty\s*item\.status = status)'
serv_upd_body3_rep = """item.name = name
        item.category = category
        item.description = description
        item.selling_price = price
        item.cost = cost_price
        item.unit_type = unit_type
        item.max_available = available_qty
        item.status = status
        item.is_hidden = (visibility == "hidden")"""
content = re.sub(serv_upd_body3, serv_upd_body3_rep, content)


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Backend updated.")
