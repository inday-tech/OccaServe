import re
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find modal ids more broadly
ids = re.findall(r'id=["\']([^"\']+)["\']', content)
modal_ids = [i for i in ids if 'modal' in i.lower() or 'Modal' in i]
print("Modal IDs:", modal_ids[:20])
