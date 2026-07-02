import re

with open(r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py', 'r', encoding='utf-8') as f:
    text = f.read()

matches = re.finditer(r'@router\.get\("(.*?)"\)\s*async def (.*?)\(', text)
for m in matches:
    print(m.group(1), m.group(2))
