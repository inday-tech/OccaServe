import re
with open('templates/caterer/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("dateClick: function(info) { {", "dateClick: function(info) {")

with open('templates/caterer/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed JS syntax")
