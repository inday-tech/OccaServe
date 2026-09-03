import re
from jinja2 import Environment, FileSystemLoader

# 1. Check Jinja2 compiles
env = Environment(loader=FileSystemLoader('templates'))
try:
    env.get_template('caterer/calendar.html')
    print("OK: Template compiles")
except Exception as e:
    print(f"ERROR: Template error: {e}")

# 2. Check block structure
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

blocks = re.findall(r'\{% block (\w+) %\}', content)
endblocks = len(re.findall(r'\{% endblock %\}', content))
print(f"Blocks: {blocks}")
print(f"Endblocks: {endblocks}")

# Check script tags are balanced
open_scripts = len(re.findall(r'<script[^>]*>', content))
close_scripts = len(re.findall(r'</script>', content))
print(f"Script tags: {open_scripts} open, {close_scripts} close")

# Check cal-grid opens and closes
cal_grid_open = content.count('class="cal-grid"')
cal_grid_close_marker = content.count('end cal-grid')
print(f"cal-grid open: {cal_grid_open}, end markers: {cal_grid_close_marker}")

# Check addScheduleModal
sched_modal = len(re.findall(r'id="addScheduleModal"', content))
print(f"addScheduleModal: {sched_modal} occurrence(s)")
