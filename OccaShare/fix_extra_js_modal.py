import re

with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the extra_js block
js_block_start = content.find('{% block extra_js %}')
js_block_end = content.rfind('{% endblock %}')

# Find all occurrences 
occurrences = [m.start() for m in re.finditer(r'<!-- Add Schedule Modal -->', content)]
print(f"Found {len(occurrences)} occurrences at: {occurrences}")
print(f"extra_js: {js_block_start} to {js_block_end}")

# Remove the one inside extra_js block
for occ in occurrences:
    if js_block_start < occ < js_block_end:
        # Find ending </div> then \n{% endblock %}
        search_from = occ
        # find the closing </div>\n of the modal (the outermost one)
        # The modal structure is: <div id="addScheduleModal">...<div>...<div>...</div></div></div>
        # We need to find balanced closing 
        depth = 0
        pos = occ
        while pos < len(content):
            if content[pos:pos+4] == '<div':
                depth += 1
            elif content[pos:pos+6] == '</div>':
                depth -= 1
                if depth == 0:
                    modal_end = pos + 6
                    # Remove from occ to modal_end
                    content = content[:occ] + content[modal_end:]
                    print(f"Removed extra_js modal at {occ}, ends at {modal_end}")
                    break
            pos += 1
        break

with open('templates/caterer/calendar.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
