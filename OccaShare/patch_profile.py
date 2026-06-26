import re
with open(r'C:\OccaServe\OccaShare\templates\caterer\profile.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_inc = '''                {% if pkg.menu_items %}
                    {% for m in pkg.menu_items %}
                        "Dish: {{ m.name }} ({{ m.category }})",
                    {% endfor %}
                {% endif %}
                {% if pkg.inclusions and pkg.inclusions is iterable %}
                    {% for inc in pkg.inclusions %}
                        "{{ inc }}",
                    {% endfor %}
                {% endif %}'''

new_inc = '''                {% if pkg.menu_items %}
                    {% for m in pkg.menu_items %}
                        "Dish: {{ m.name }} ({{ m.category }})",
                    {% endfor %}
                {% endif %}
                {% if pkg.equipment_links %}
                    {% for eq_link in pkg.equipment_links %}
                        "Equipment: {{ eq_link.equipment.name }} {% if eq_link.quantity > 1 %}(x{{ eq_link.quantity }}){% endif %}",
                    {% endfor %}
                {% endif %}
                {% if pkg.service_links %}
                    {% for svc_link in pkg.service_links %}
                        "Service: {{ svc_link.service.name }} {% if svc_link.quantity > 1 %}(x{{ svc_link.quantity }}){% endif %}",
                    {% endfor %}
                {% endif %}
                {% if pkg.inclusions and pkg.inclusions is iterable %}
                    {% for inc in pkg.inclusions %}
                        "{{ inc }}",
                    {% endfor %}
                {% endif %}'''

content = content.replace(old_inc, new_inc)

with open(r'C:\OccaServe\OccaShare\templates\caterer\profile.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done patching profile.html")
