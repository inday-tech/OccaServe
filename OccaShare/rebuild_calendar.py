import shutil, re, os

# Step 1: Backup the broken file
shutil.copy('templates/caterer/calendar.html', 'templates/caterer/calendar.html.broken_bak')
print("Backed up broken file")

# Step 2: Read the clean backup
with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    backup = f.read()

# Step 3: Extract each block from backup
def get_block(name, text):
    pattern = rf'\{{% block {name} %\}}([\s\S]*?)\{{% endblock %\}}'
    m = re.search(pattern, text)
    return m.group(1) if m else ''

css_block = get_block('extra_css', backup)
js_block = get_block('extra_js', backup)
content_block = get_block('content', backup)

print(f"CSS block: {len(css_block)} chars")
print(f"JS block: {len(js_block)} chars")
print(f"Content block: {len(content_block)} chars")

# Step 4: Check if walk-in modal is in backup content
if 'manualBookingModal' in backup:
    print("Walk-in modal: PRESENT in backup")
else:
    print("Walk-in modal: MISSING in backup")
    
# Step 5: Check sidebar structure in backup
if 'sidebarSelectedDateStr' in backup:
    print("Sidebar Selected Date: PRESENT in backup")
else:
    print("Sidebar Selected Date: MISSING in backup")
    
# Step 6: Check filter bar in backup
if 'filter-btn' in backup:
    print("Filter bar: PRESENT in backup")
else:
    print("Filter bar: MISSING in backup")

# Step 7: Check addScheduleModal in backup
if 'addScheduleModal' in backup:
    print("Add Schedule Modal: PRESENT in backup")
else:
    print("Add Schedule Modal: MISSING in backup")
