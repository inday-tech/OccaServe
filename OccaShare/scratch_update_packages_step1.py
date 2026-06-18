import re

filepath_router = 'c:/OccaServe/OccaShare/app/routers/caterer_dashboard.py'
with open(filepath_router, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace manage_packages route
manage_packages_pattern = r'@router\.get\("/packages".*?return templates\.TemplateResponse\("caterer/packages\.html", \{\n\s+"request": request,\n\s+"user": user,\n\s+"packages": active_packages,\n\s+"menu_items": active_menu,\n\s+"services": active_services,\n\s+"active_page": "packages"\n\s+\}\)'
manage_packages_replacement = """@router.get("/packages", response_class=HTMLResponse)
async def manage_packages(
    request: Request, 
    db: Session = Depends(database.get_db),
    user: models.User = Depends(caterer_only)
):
    profile = user.caterer_profile
    active_packages = [p for p in profile.packages if p.status != 'archived']
    
    # Filter menu items (Dishes)
    service_cats = ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']
    active_menu = [m for m in profile.menu_items if not m.is_archived and m.category not in service_cats]
    
    # Compile Inventory & Services
    equipment_items = [e for e in profile.equipment_items if not e.is_archived]
    service_items = [s for s in profile.service_items if not s.is_archived]
    legacy_items = [m for m in profile.menu_items if not m.is_archived and m.category in service_cats]
    
    # Unify them into a dictionary format compatible with the template
    active_services = []
    for e in equipment_items:
        active_services.append({
            "id": f"eq_{e.id}",
            "real_id": e.id,
            "type": "Equipment",
            "name": e.name,
            "category": e.category,
            "cost_price": e.cost_value,
            "image_url": e.image_url
        })
    for s in service_items:
        active_services.append({
            "id": f"sv_{s.id}",
            "real_id": s.id,
            "type": "Service",
            "name": s.name,
            "category": s.category,
            "cost_price": s.cost,
            "image_url": s.image_url
        })
    for m in legacy_items:
        active_services.append({
            "id": m.id, # legacy uses int ID
            "real_id": m.id,
            "type": "Legacy",
            "name": m.name,
            "category": m.category,
            "cost_price": m.cost_price,
            "image_url": m.image_url
        })
        
    return templates.TemplateResponse("caterer/packages.html", {
        "request": request,
        "user": user,
        "packages": active_packages,
        "menu_items": active_menu,
        "services": active_services,
        "active_page": "packages"
    })"""

content = re.sub(manage_packages_pattern, manage_packages_replacement, content, flags=re.DOTALL)

with open(filepath_router, 'w', encoding='utf-8') as f:
    f.write(content)


# Update packages.html
filepath_html = 'c:/OccaServe/OccaShare/templates/caterer/packages.html'
with open(filepath_html, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Replace "Included Equipment & Services" -> "Included Inventory & Services"
html_content = html_content.replace('Included Equipment & Services', 'Included Inventory & Services')
# Also inside script id references? Wait, let me just fix the data-id binding inside the loop
# The loop looks like: <div class="menu-select-card" data-id="{{ item.id }}" ...>

with open(filepath_html, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Updated manage_packages and packages.html terms")
