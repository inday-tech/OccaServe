# Check JS syntax (brace balance)
with open('app/static/js/caterer/calendar.js', 'r', encoding='utf-8') as f:
    js = f.read()

count = 0
for char in js:
    if char == '{': count += 1
    elif char == '}': count -= 1
print(f'JS brace balance: {count} (should be 0)')

paren = 0
for char in js:
    if char == '(': paren += 1
    elif char == ')': paren -= 1
print(f'JS paren balance: {paren} (should be 0)')

# Check template - Jinja2
from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('templates'))
try:
    env.get_template('caterer/calendar.html')
    print('Template: OK')
except Exception as e:
    print(f'Template ERROR: {e}')

# Check key functions
fns = ['openManualBookingModal', 'openAddScheduleModal', 'saveSchedule', 'updateSidebarForDate', 'changeStep']
for fn in fns:
    print(f'  {fn}: {"OK" if fn in js else "MISSING"}')

print()
print('All done!')
