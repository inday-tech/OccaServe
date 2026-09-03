import re
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find ALL ids
ids = re.findall(r'id=["\']([^"\']+)["\']', content)
print("ALL IDs found:", sorted(set(ids)))
