import re
with open(r'C:\OccaServe\OccaShare\templates\caterer\packages.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'packages.js\?v=\d+\.\d+', 'packages.js?v=34.0', content)
content = re.sub(r'packages.css\?v=\d+\.\d+', 'packages.css?v=34.0', content)

with open(r'C:\OccaServe\OccaShare\templates\caterer\packages.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
