import re
f = r'c:\OccaServe\OccaShare\templates\caterer\layout.html'
with open(f, 'r', encoding='utf-8') as file:
    content = file.read()

pattern = r'\s*<li>\s*<a href="/caterer/compliance"[^>]*>\s*<div[^>]*><i class="fas fa-shield-halved"></i></div>\s*<span class="nav-label">Identity Verification</span>\s*</a>\s*</li>'
content = re.sub(pattern, '', content)

with open(f, 'w', encoding='utf-8') as out:
    out.write(content)
print('Removed from layout.html')
