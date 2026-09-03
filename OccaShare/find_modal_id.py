import re
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

ids = re.findall(r'id=["\'](\w+Modal)["\']', content)
print("Modal IDs found:", ids)
