import re
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Find all divs with id containing modal
matches = re.finditer(r'<div[^>]*id=[\'"]([^\'"]*modal[^\'"]*|eventModal)[\'"][^>]*>', content, re.IGNORECASE)
for m in matches:
    print(f"Modal ID: {m.group(1)} at line {content[:m.start()].count(chr(10))+1}")
