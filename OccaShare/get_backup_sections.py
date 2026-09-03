with open('templates/caterer/calendar_backup.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Find each block's content
def get_block(name, text):
    pattern = rf'\{{% block {name} %\}}([\s\S]*?)\{{% endblock %\}}'
    m = re.search(pattern, text)
    if m:
        return m.group(1)
    return ''

extra_css = get_block('extra_css', content)
main_content = get_block('content', content)
extra_js = get_block('extra_js', content)

print(f"extra_css length: {len(extra_css)}")
print(f"content length: {len(main_content)}")
print(f"extra_js length: {len(extra_js)}")

# Check backup has calendar div
print('Calendar div in content:', 'id=\'calendar\'' in main_content or 'id=\"calendar\"' in main_content)
print('manualBookingModal in backup:', 'manualBookingModal' in content)
