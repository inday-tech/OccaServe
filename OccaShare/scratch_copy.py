import os

with open('c:/OccaServe/OccaShare/templates/customer/caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('{% extends "customer/layout.html" %}', '{% extends "landing_base.html" %}')
content = content.replace("{% set active_page = 'marketplace' %}\n", "")
content = content.replace('<div class="hub-container">', '<div class="hub-container" style="margin-top: 80px;">')

with open('c:/OccaServe/OccaShare/templates/caterer/profile.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement successful")
