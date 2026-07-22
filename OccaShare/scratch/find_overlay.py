import re

with open(r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    text = f.read()

print(re.findall(r'class="[^"]*(?:load|overlay|spinner|modal-layer)[^"]*"', text))
