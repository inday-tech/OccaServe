import codecs
import re

file_path = 'c:\\OccaServe\\OccaShare\\app\\routers\\customer_dashboard.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

# 1. active_menu filter (no escape bug)
content = re.sub(
    r"and m\.category not in \['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages'\]\s*\]",
    r"and m.category not in ['Rentals', 'Services', 'Event Styling', 'Event Rental', 'Entertainment', 'Event Coordination', 'Food Cart', 'Equipment Rental', 'Staffing Services', 'Packages']\n        and getattr(m, 'usage_type', '') != 'package_only'\n    ]",
    content
)

# 2. active_inventory display_type
# The original has:
# active_inventory = active_services + active_equipment
# 
#     # Check for previous relationship
target = "    active_inventory = active_services + active_equipment\n"
replacement = """    active_inventory = active_services + active_equipment

    for item in active_inventory:
        item.display_price = getattr(item, 'rental_price', getattr(item, 'selling_price', 0))
        item.display_type = 'Equipment' if hasattr(item, 'equipment_type') else 'Service'
        item.display_qty = getattr(item, 'available_qty', getattr(item, 'max_available', 1))
        item.deposit_pct = getattr(item, 'security_deposit_pct', 0)
        item.needs_kyc = getattr(item, 'requires_kyc', False)
        item.min_hours = getattr(item, 'minimum_hours', getattr(item, 'base_duration_hours', None))
"""
content = content.replace(target, replacement)

# 3. db.refresh and Cache-Control
old_return = """    # Check for previous relationship
    has_previous_bookings = db.query(models.Booking).filter("""

new_return = """    # Force DB Refresh to prevent stale data
    db.refresh(caterer)

    # Check for previous relationship
    has_previous_bookings = db.query(models.Booking).filter("""

content = content.replace(old_return, new_return)

pattern = re.compile(r'    return templates\.TemplateResponse\("customer/caterer_profile_view\.html", \{.*?\n    \}\)', re.DOTALL)
new_ret = """    response = templates.TemplateResponse("customer/caterer_profile_view.html", {
        "request": request, 
        "caterer": caterer,
        "packages": active_packages,
        "active_menu": active_menu,
        "active_inventory": active_inventory,
        "gallery_items": caterer.gallery_items,
        "public_portfolios": public_portfolios,
        "reviews": caterer.reviews,
        "user": user,
        "has_previous_bookings": has_previous_bookings,
        "has_previous_communication": has_previous_communication,
        "caterer_unavailable": caterer_unavailable,
        "active_page": "marketplace",
        "nav_page": "caterers"
    })
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response"""
content = pattern.sub(new_ret, content)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)
