import re

# Read the broken current calendar.html
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    broken = f.read()

# Read the clean backup
with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    backup = f.read()

# ============================================================
# STRATEGY: Extract the GOOD parts from the broken file
# (content and extra_js blocks are there but unreachable due
# to broken title block), fix the header, and reassemble.
# ============================================================

# 1) Get clean extra_css from backup (it's fine there)
def get_block(name, text):
    pattern = rf'\{{% block {name} %\}}([\s\S]*?)\{{% endblock %\}}'
    m = re.search(pattern, text)
    return m.group(1) if m else ''

css_from_backup = get_block('extra_css', backup)

# 2) Get content block from BROKEN (it has filter bar, sidebar, cal div, modals)
cb_start = broken.find('{% block content %}')
cb_end = broken.find('{% endblock %}', cb_start)
content_body = broken[cb_start + len('{% block content %}'):cb_end]

# 3) Get extra_js from BROKEN (has FullCalendar loader + window vars)
js_start = broken.find('{% block extra_js %}')
js_end = broken.rfind('{% endblock %}')
js_body = broken[js_start + len('{% block extra_js %}'):js_end]

print(f"CSS body: {len(css_from_backup)}")
print(f"Content body: {len(content_body)}")
print(f"JS body: {len(js_body)}")

# 4) Check that the content block has what we need
checks = ['cal-grid', 'id=\'calendar\'', 'cal-sidebar', 'filter-btn', 'sidebarDayEvents', 'addScheduleModal', 'manualBookingModal']
for c in checks:
    print(f"  {c}: {'YES' if c in content_body else 'NO'}")
