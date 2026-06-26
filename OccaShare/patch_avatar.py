import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_unsplash = """{% set final_img = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=400' %}"""

new_avatar = """{% set final_img = 'https://ui-avatars.com/api/?name=' ~ (cat|urlencode) ~ '&background=f1f5f9&color=FF7B54&size=400&font-size=0.33&bold=true' %}"""

content = content.replace(old_unsplash, new_avatar)

with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Restored UI Avatars with better styling")
