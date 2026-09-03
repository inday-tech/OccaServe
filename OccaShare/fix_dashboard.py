import re

with open('app/routers/caterer_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("identity_requests = sum(1 for b in bookings if not getattr(b.user, 'is_verified', True))", "identity_requests = 0")

with open('app/routers/caterer_dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated caterer_dashboard.py')
