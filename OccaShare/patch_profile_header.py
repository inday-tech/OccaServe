import re

path = 'templates/customer/caterer_profile_view.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                    <div class="meta-pill"><i class="fas fa-eye"></i> <span>{{ caterer.profile_views or 0 }} Views</span></div>"""
replacement = """                    <div class="meta-pill"><i class="fas fa-eye"></i> <span>{{ caterer.profile_views or 0 }} Views</span></div>
                    <div class="meta-pill"><i class="fas fa-clock"></i> <span>{{ caterer.equipment_turnover_hours if caterer.equipment_turnover_hours is not none else 24 }}h Turnover Buffer</span></div>"""
content = content.replace(target, replacement)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Added Turnover Hours to profile header meta pills!")
