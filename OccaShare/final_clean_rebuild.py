import re

# Read the clean backup as foundation
with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    backup = f.read()

# Read the broken current file (which has sidebar updates and filter bar we want)
with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    broken = f.read()

def get_block(name, text):
    pattern = rf'\{{% block {name} %\}}([\s\S]*?)\{{% endblock %\}}'
    m = re.search(pattern, text)
    return m.group(1) if m else ''

# CSS from backup (has all the needed styles)
css_body = get_block('extra_css', backup)

# JS from broken file (has all the modal and calendar JS) - just the extra_js block
js_start = broken.find('{% block extra_js %}')
js_end = broken.rfind('{% endblock %}')
js_body = broken[js_start + len('{% block extra_js %}'):js_end]

# Content: we need to carefully construct this
# We want:
# 1. Page header (with Walk-in Booking and Add Schedule buttons)
# 2. Filter bar
# 3. cal-grid (calendar + sidebar)
# 4. Availability section (sidebar form, capacity form)
# 5. Modals (addScheduleModal, manualBookingModal, blockedDateModal)
# 6. Inline script for walk-in wizard (changeStep, addQuotationRow etc)
# We do NOT want duplicate modals.

# Get the content block from broken file
cb_start = broken.find('{% block content %}')
cb_end = broken.find('{% endblock %}', cb_start)
content_body = broken[cb_start + len('{% block content %}'):cb_end]

# Remove the second manualBookingModal (find both, keep only one)
# Strategy: find all occurrences of '<div id="manualBookingModal"' and remove from the second one
modal_marker = '<div id=\"manualBookingModal\" class=\"occ-modal-overlay\">'
first_pos = content_body.find(modal_marker)
second_pos = content_body.find(modal_marker, first_pos + 1)

if second_pos != -1:
    # Find the end of the second modal (count divs)
    depth = 0
    pos = second_pos
    while pos < len(content_body):
        if content_body[pos:pos+4] == '<div':
            depth += 1
        elif content_body[pos:pos+5] == '</div':
            depth -= 1
            if depth == 0:
                end_of_second = pos + 6
                break
        pos += 1
    content_body = content_body[:second_pos] + content_body[end_of_second:]
    print(f"Removed second manualBookingModal (was at position {second_pos})")

# Also remove the inline script from content (it's the walk-in wizard that should be inline)
# Actually, keep it as it is since changeStep and addQuotationRow are used inline
# The inline script tag in content block is fine

# Now rebuild
clean_file = (
    "{% set nav_page = 'calendar' %}\n"
    "{% extends \"caterer/layout.html\" %}\n"
    "\n"
    "{% block title %}Service Calendar - Caterer Dashboard{% endblock %}\n"
    "\n"
    "{% block extra_css %}\n"
    + css_body +
    "{% endblock %}\n"
    "\n"
    "{% block content %}\n"
    + content_body +
    "{% endblock %}\n"
    "\n"
    "{% block extra_js %}\n"
    + js_body +
    "{% endblock %}\n"
)

# Validate
blocks = len(re.findall(r'\{% block \w+ %\}', clean_file))
endblocks = len(re.findall(r'\{% endblock %\}', clean_file))
print(f"Blocks: {blocks}, Endblocks: {endblocks}")

modal_count = clean_file.count('id=\"manualBookingModal\"')
print(f"manualBookingModal occurrences: {modal_count}")

sched_modal_count = clean_file.count('id=\"addScheduleModal\"')
print(f"addScheduleModal occurrences: {sched_modal_count}")

calendar_div = "id='calendar'" in clean_file
print(f"Calendar div present: {calendar_div}")

filter_bar = 'filter-btn' in clean_file
print(f"Filter bar present: {filter_bar}")

sidebar = 'sidebarDayEvents' in clean_file
print(f"Sidebar day events present: {sidebar}")

# Write it
with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(clean_file)
print(f"\nWritten {len(clean_file)} chars to calendar.html")
