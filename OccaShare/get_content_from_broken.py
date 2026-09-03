with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Get everything from broken file between content block markers
cb_start = content.find('{% block content %}')
cb_end = content.find('{% endblock %}', cb_start) 
content_section = content[cb_start+len('{% block content %}'):cb_end]

lines = content_section.split('\n')
print(f"Content block lines: {len(lines)}")
# Check what's inside
checks = ['id=\'calendar\'', 'id=\"calendar\"', 'cal-grid', 'cal-sidebar', 'addScheduleModal', 'filter-btn', 'sidebarDayEvents']
for c in checks:
    found = c in content_section
    print(f"  {c}: {'YES' if found else 'NO'}")
