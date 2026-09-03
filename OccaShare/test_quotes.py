import re

with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # remove comments
    line = re.sub(r'//.*', '', line)
    
    # remove all valid string literals
    line = re.sub(r'\"(?:\\.|[^\\\"])*\"', '', line)
    line = re.sub(r'\'(?:\\.|[^\\\'])*\'', '', line)
    
    if '"' in line or "'" in line:
        print(f'Line {i+1} has unbalanced quote: {line.strip()}')
