import re

path = 'app/main.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "from app.routers import website, auth, admin, bookings, caterers, packages, caterer_dashboard, customer_dashboard, verification, contact, quotations, kyc, payments, notifications, chat, caterer_feed"
replacement = "from app.routers import website, auth, admin, bookings, caterers, packages, caterer_dashboard, customer_dashboard, verification, contact, quotations, kyc, payments, notifications, chat, caterer_feed, inventory_api"
content = content.replace(target, replacement)

target2 = "app.include_router(caterer_feed.router)"
replacement2 = "app.include_router(caterer_feed.router)\napp.include_router(inventory_api.router)"
content = content.replace(target2, replacement2)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched main.py!")
