with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
import re

def get_block(name, text):
    pattern = rf'\{{% block {name} %\}}([\s\S]*?)\{{% endblock %\}}'
    m = re.search(pattern, text)
    if m:
        return m.group(1)
    return ''
    
main_content = get_block('content', content)

# Look for filter bar and cal-grid structure
lines = main_content.split('\n')
for i, line in enumerate(lines):
    if 'filter-btn' in line or 'cal-grid' in line or 'cal-sidebar' in line or 'calendar' in line.lower():
        print(f"{i+1}: {line.strip()}")
