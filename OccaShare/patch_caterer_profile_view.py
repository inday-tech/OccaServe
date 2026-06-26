import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        inclusions: {{ (pkg.inclusions)|tojson if pkg.inclusions else '[]' }},
        linked_inventory: [{% for item in pkg.menu_items %}{% if item.category in ['Rentals', 'Services'] %}{{ item.name|tojson }},{% endif %}{% endfor %}].filter(Boolean),'''

new = '''        inclusions: {{ (pkg.inclusions)|tojson if pkg.inclusions else '[]' }},
        linked_inventory: [
            {% for item in pkg.menu_items %}{% if item.category in ['Rentals', 'Services'] %}{{ item.name|tojson }},{% endif %}{% endfor %}
            {% if pkg.equipment_links %}{% for el in pkg.equipment_links %}{{ el.equipment.name|tojson }},{% endfor %}{% endif %}
            {% if pkg.service_links %}{% for sl in pkg.service_links %}{{ sl.service.name|tojson }},{% endfor %}{% endif %}
        ].filter(Boolean),'''

content = content.replace(old, new)

with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching caterer_profile_view.html")
