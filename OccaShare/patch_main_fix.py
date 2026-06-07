import re

path = 'app/main.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "from .routers import website, auth, admin, bookings, social_auth, caterers, packages, caterer_dashboard, customer_dashboard, verification, kyc, quotations, payments, contact, notifications, chat, caterer_feed"
replacement = "from .routers import website, auth, admin, bookings, social_auth, caterers, packages, caterer_dashboard, customer_dashboard, verification, kyc, quotations, payments, contact, notifications, chat, caterer_feed, inventory_api"
content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched main.py import correctly!")
