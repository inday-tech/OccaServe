import codecs
import re

file_path = 'c:\\OccaServe\\OccaShare\\app\\routers\\customer_dashboard.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

# Fix active_menu logic
content = re.sub(
    r'and m\.category not in \[\'Rentals\', \'Services\', \'Event Styling\', \'Event Rental\',\s*\'Entertainment\', \'Event Coordination\', \'Food Cart\',\s*\'Equipment Rental\', \'Staffing Services\', \'Packages\'\]\s*\]',
    r'and m.category not in [\'Rentals\', \'Services\', \'Event Styling\', \'Event Rental\', \'Entertainment\', \'Event Coordination\', \'Food Cart\', \'Equipment Rental\', \'Staffing Services\', \'Packages\']\n        and getattr(m, \'usage_type\', \'\') != \'package_only\'\n    ]',
    content
)

# Fix active_services logic
content = re.sub(
    r'active_services = \[\n        s for s in getattr\(caterer, \'service_items\', \[\]\)\n        if not s\.is_archived and not s\.is_hidden and s\.status == \'available\'\n    \]',
    r'active_services = [\n        s for s in getattr(caterer, \'service_items\', [])\n        if not s.is_archived and not s.is_hidden and s.status == \'available\' and getattr(s, \'usage_type\', \'\') != \'package_only\'\n    ]',
    content
)

# Fix active_equipment logic
content = re.sub(
    r'active_equipment = \[\n        e for e in getattr\(caterer, \'equipment_items\', \[\]\)\n        if not e\.is_archived and not e\.is_hidden and e\.status == \'available\'\n    \]',
    r'active_equipment = [\n        e for e in getattr(caterer, \'equipment_items\', [])\n        if not e.is_archived and not e.is_hidden and e.status == \'available\' and getattr(e, \'usage_type\', \'\') != \'package_only\'\n    ]',
    content
)

# Fix return templates and add headers
old_return = """    # Check for previous relationship
    has_previous_bookings = db.query(models.Booking).filter("""

new_return = """    # Force DB Refresh to prevent stale data
    db.refresh(caterer)

    # Check for previous relationship
    has_previous_bookings = db.query(models.Booking).filter("""

content = content.replace(old_return, new_return)

content = re.sub(
    r'        \}\)\n\n@router\.get\("/bookings"',
    r'        })\n    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"\n    return response\n\n@router.get("/bookings"',
    content
)

# Wait, the return statement in customer_dashboard.py for caterer_detail might be different. Let's use a more robust replacement.
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
