import re

with open('templates/caterer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'href="{{ url_for\(\'static\', path=\'/css/caterer/index\.css\'\) }}\?v=[0-9.]+"', 'href="{{ url_for(\'static\', path=\'/css/caterer/index.css\') }}?v=12.5"', content)

with open('templates/caterer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
