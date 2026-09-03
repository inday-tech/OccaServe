with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# The whole problem: block title isn't closed correctly.
# Lines 1-53 have the broken block title. We need to:
# 1. Fix block title (single line)
# 2. Remove the first duplicate of addScheduleModal (lines 357-405) that created extra endblock
# 3. Remove the third duplicate at the very end (lines 826-872 inside extra_js block)

# Step 1: Fix the block title - it should just be one line
lines = content.split('\n')

# Find block title start
title_start = None
for i, line in enumerate(lines):
    if '{% block title %}' in line:
        title_start = i
        break

# Replace from title_start until '{% endblock %}' with clean single line
if title_start is not None:
    # Find next endblock after title_start
    title_end = None
    for i in range(title_start, title_start + 60):
        if i < len(lines) and '{% endblock %}' in lines[i]:
            title_end = i
            break
    
    if title_end is not None:
        print(f"Replacing lines {title_start+1} to {title_end+1}")
        new_title = '{% block title %}Service Calendar{% endblock %}'
        lines = lines[:title_start] + [new_title] + lines[title_end+1:]

# Step 2: Now find duplicate addScheduleModal blocks (inside extra_css block and inside extra_js block)
# Rejoin and work with new content
content = '\n'.join(lines)

# Find all occurrences of addScheduleModal opening div
import re

occurrences = [m.start() for m in re.finditer(r'<!-- Add Schedule Modal -->', content)]
print(f"Found {len(occurrences)} Schedule Modal occurrences at positions: {occurrences}")

# We want to keep ONLY the one inside the content block (around line 826 in original, now shifted)
# We'll remove the first one which is inside extra_css, and the third one inside extra_js
# They will be at occurrences[0], occurrences[1], occurrences[2] - keep only the LAST one before extra_js

# Strategy: remove all occurrences that are within block extra_css or block extra_js
# Find block extra_css range
css_block_start = content.find('{% block extra_css %}')
css_block_end = content.find('{% endblock %}', css_block_start)

# Find block extra_js range  
js_block_start = content.find('{% block extra_js %}')
js_block_end = content.rfind('{% endblock %}')

print(f"extra_css block: {css_block_start} to {css_block_end}")
print(f"extra_js block: {js_block_start} to {js_block_end}")

# Remove modals that are inside extra_css block
for occ in sorted(occurrences, reverse=True):
    if css_block_start < occ < css_block_end:
        # find the end of this modal (closing </div>)
        modal_end = content.find('</div>\n\n{% endblock %}', occ)
        if modal_end == -1:
            modal_end = content.find('</div>\n{% endblock %}', occ)
        if modal_end != -1:
            modal_end = content.find('</div>', modal_end) + len('</div>')
            content = content[:occ] + content[modal_end:]
            print(f"Removed modal at {occ}")
        # Also try finding the next endblock
        break

# Recalculate occurrences after removal
occurrences = [m.start() for m in re.finditer(r'<!-- Add Schedule Modal -->', content)]
print(f"After first removal: {len(occurrences)} Schedule Modal occurrences")

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(content)
    
print("Done fixing template blocks")
