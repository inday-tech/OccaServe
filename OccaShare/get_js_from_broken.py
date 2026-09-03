with open('templates/caterer/calendar.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Get the calendar.js script tag  
js_block_start = content.find('{% block extra_js %}')
js_block_end = content.rfind('{% endblock %}')
js_section = content[js_block_start:js_block_end+14]
print(f"JS block length: {len(js_section)}")
print("First 500 chars:")
print(js_section[:500])
