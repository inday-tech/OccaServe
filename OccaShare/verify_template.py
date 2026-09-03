import re

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check block structure
blocks = re.findall(r'\{% block \w+ %\}', content)
endblocks = re.findall(r'\{% endblock %\}', content)
print(f"Blocks: {blocks}")
print(f"Endblock count: {len(endblocks)}")

# Check block title
title_line = [l for l in content.split('\n') if '{% block title %}' in l]
print(f"Title block: {title_line}")

# Check for schedule modal occurrences
occ = [m.start() for m in re.finditer(r'id=\"addScheduleModal\"', content)]
print(f"addScheduleModal occurrences: {len(occ)}")

# Check calendar div
cal = [l for l in content.split('\n') if "id='calendar'" in l or 'id=\"calendar\"' in l]
print(f"Calendar div: {cal}")

# Check JS buttons
btn_walkin = [l for l in content.split('\n') if 'openManualBookingModal' in l]
btn_sched = [l for l in content.split('\n') if 'openAddScheduleModal' in l]
print(f"Walk-in button: {len(btn_walkin)} occurrences")
print(f"Add Schedule button: {len(btn_sched)} occurrences")
