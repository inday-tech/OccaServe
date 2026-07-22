import codecs
import re

file_path = 'c:\\OccaServe\\OccaShare\\app\\routers\\caterers.py'
with codecs.open(file_path, 'r', 'utf-8') as f:
    content = f.read()

# Fix active_menu logic
content = re.sub(
    r'and m\.category not in \[\'Rentals\', \'Services\', \'Event Styling\', \'Event Rental\',\s*\'Entertainment\', \'Event Coordination\', \'Food Cart\',\s*\'Equipment Rental\', \'Staffing Services\', \'Packages\'\]\s*and m\.usage_type != \'package_only\'\s*\]',
    r'and m.category not in [\'Rentals\', \'Services\', \'Event Styling\', \'Event Rental\', \'Entertainment\', \'Event Coordination\', \'Food Cart\', \'Equipment Rental\', \'Staffing Services\', \'Packages\']\n        and getattr(m, \'usage_type\', \'\') != \'package_only\'\n    ]',
    content
)

# Fix active_services logic
content = re.sub(
    r'active_services = \[\n        s for s in getattr\(caterer, \'service_items\', \[\]\)\n        if not s\.is_archived and not s\.is_hidden and s\.status == \'available\'\n        and s\.usage_type != \'package_only\'\n    \]',
    r'active_services = [\n        s for s in getattr(caterer, \'service_items\', [])\n        if not s.is_archived and not s.is_hidden and s.status == \'available\' and getattr(s, \'usage_type\', \'\') != \'package_only\'\n    ]',
    content
)

# Fix active_equipment logic
content = re.sub(
    r'active_equipment = \[\n        e for e in getattr\(caterer, \'equipment_items\', \[\]\)\n        if not e\.is_archived and not e\.is_hidden and e\.status == \'available\'\n        and e\.usage_type != \'package_only\'\n    \]',
    r'active_equipment = [\n        e for e in getattr(caterer, \'equipment_items\', [])\n        if not e.is_archived and not e.is_hidden and e.status == \'available\' and getattr(e, \'usage_type\', \'\') != \'package_only\'\n    ]',
    content
)

# Fix return templates and add headers
old_return = """    # If the user is a logged-in customer, show the dashboard-integrated view
    if user and user.role == "customer":
        return templates.TemplateResponse("customer/caterer_profile_view.html", {"""

new_return = """    # Force DB Refresh to prevent stale data
    db.refresh(caterer)

    # If the user is a logged-in customer, show the dashboard-integrated view
    if user and user.role == "customer":
        response = templates.TemplateResponse("customer/caterer_profile_view.html", {"""

content = content.replace(old_return, new_return)

content = re.sub(
    r'        \}\)\n\n    return templates\.TemplateResponse\("customer/caterer_profile_view\.html", \{',
    r'        })\n        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"\n        return response\n\n    response = templates.TemplateResponse("customer/caterer_profile_view.html", {',
    content
)

content = re.sub(
    r'        "nav_page": "caterers"\n    \}\)',
    r'        "nav_page": "caterers"\n    })\n    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"\n    return response',
    content
)

with codecs.open(file_path, 'w', 'utf-8') as f:
    f.write(content)
