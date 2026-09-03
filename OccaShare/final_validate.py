from jinja2 import Environment, FileSystemLoader
import re

env = Environment(loader=FileSystemLoader('templates'))
try:
    env.get_template('caterer/calendar.html')
    print('OK: Jinja2 template parses correctly')
except Exception as e:
    print(f'ERROR: {e}')

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

print(f'File size: {len(content)} chars')
blocks = re.findall(r'\{% block \w+ %\}', content)
endblocks = len(re.findall(r'\{% endblock %\}', content))
print(f'Blocks: {blocks}')
print(f'Endblocks: {endblocks}')

checks = [
    ('Calendar div', \"id='calendar'\"),
    ('Filter bar', 'filter-btn'),
    ('Cal-grid', 'cal-grid'),
    ('Sidebar', 'sidebarDayEvents'),
    ('Add Schedule Modal', 'addScheduleModal'),
    ('Walk-in Modal (1 only)', content.count('id=\"manualBookingModal\"') == 1),
    ('openManualBookingModal fn', 'openManualBookingModal'),
    ('openAddScheduleModal fn', 'openAddScheduleModal'),
    ('FullCalendar JS', 'fullcalendar'),
]
for name, check in checks:
    if isinstance(check, bool):
        print(f'  {name}: {\"YES\" if check else \"FAIL - Multiple copies!\"}')
    else:
        print(f'  {name}: {\"YES\" if check in content else \"NO\"}')
