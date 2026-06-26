import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace "A-la-carte & Rentals" with "Food Menu"
content = content.replace('<h2 class="section-title" style="margin-bottom: 1.25rem;">A-la-carte & Rentals</h2>', '<h2 class="section-title" style="margin-bottom: 1.25rem;">Food Menu</h2>')

with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Replaced section title")
