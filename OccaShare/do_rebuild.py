import re

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    broken = f.read()

with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    backup = f.read()

def get_block(name, text):
    pattern = rf'\{{% block {name} %\}}([\s\S]*?)\{{% endblock %\}}'
    m = re.search(pattern, text)
    return m.group(1) if m else ''

css_from_backup = get_block('extra_css', backup)

cb_start = broken.find('{% block content %}')
cb_end = broken.find('{% endblock %}', cb_start)
content_body = broken[cb_start + len('{% block content %}'):cb_end]

js_start = broken.find('{% block extra_js %}')
js_end = broken.rfind('{% endblock %}')
js_body = broken[js_start + len('{% block extra_js %}'):js_end]

# Reconstruct clean file
clean = (
    "{{% set nav_page = 'calendar' %}}\n"
    "{{% extends \"caterer/layout.html\" %}}\n"
    "\n"
    "{{% block title %}}Service Calendar - Caterer Dashboard{{% endblock %}}\n"
    "\n"
    "{{% block extra_css %}}\n"
    "{css}\n"
    "{{% endblock %}}\n"
    "\n"
    "{{% block content %}}\n"
    "{content}\n"
    "{{% endblock %}}\n"
    "\n"
    "{{% block extra_js %}}\n"
    "{js}\n"
    "{{% endblock %}}\n"
).format(css=css_from_backup, content=content_body, js=js_body)

# Remove the double {{ }} that result from format() - wait we used {{% %}} style so let's fix properly
# Actually we need to just concatenate directly, not use .format()
clean = (
    "{% set nav_page = 'calendar' %}\n"
    "{% extends \"caterer/layout.html\" %}\n"
    "\n"
    "{% block title %}Service Calendar - Caterer Dashboard{% endblock %}\n"
    "\n"
    "{% block extra_css %}\n"
    + css_from_backup +
    "\n{% endblock %}\n"
    "\n"
    "{% block content %}\n"
    + content_body +
    "\n{% endblock %}\n"
    "\n"
    "{% block extra_js %}\n"
    + js_body +
    "\n{% endblock %}\n"
)

# Validate
print(f"Final file length: {len(clean)}")
blocks = len(re.findall(r'\{% block \w+ %\}', clean))
endblocks = len(re.findall(r'\{% endblock %\}', clean))
print(f"Blocks: {blocks}, Endblocks: {endblocks}")

# Check key elements
checks = [
    ("Calendar div", "id='calendar'"),
    ("Filter bar", "filter-btn"),
    ("Cal-grid", "cal-grid"),
    ("Sidebar", "cal-sidebar"),
    ("Sidebar day events", "sidebarDayEvents"),
    ("Add Schedule Modal", "addScheduleModal"),
    ("Walk-in Modal", "manualBookingModal"),
    ("FullCalendar JS", "fullcalendar"),
    ("Jinja block title ok", "{% block title %}Service Calendar"),
]
for name, c in checks:
    print(f"  {name}: {'YES' if c in clean else 'NO'}")

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(clean)
print("\nFile written successfully!")
