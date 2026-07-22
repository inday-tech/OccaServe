import re

html_path = r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace my old fix with the new attributes
content = re.sub(
    r'\{% set item_price = \(item\.rental_price if item\.__tablename__ == \'equipment\' else item\.selling_price\) or 0 %\}',
    '{% set item_price = item.display_price or 0 %}',
    content
)
content = re.sub(
    r'\{\{ \(item\.rental_price if item\.__tablename__ == \'equipment\' else item\.selling_price\)\|tojson \}\}',
    '{{ (item.display_price or 0)|tojson }}',
    content
)
content = re.sub(
    r'\"\{\{ \'Equipment\' if item\.__tablename__ == \'equipment\' else \'Service\' \}\}\"',
    '{{ item.display_type|tojson }}',
    content
)
# Also need to replace the original bad logic just in case it wasn't replaced fully
content = re.sub(
    r'\{% set item_price = \(item\.rental_price if item\.rental_price is defined else item\.selling_price\) or 0 %\}',
    '{% set item_price = item.display_price or 0 %}',
    content
)
content = re.sub(
    r'price: \{\{ \(item\.rental_price if item\.rental_price is defined else item\.selling_price\)\|tojson \}\},',
    'price: {{ (item.display_price or 0)|tojson }},',
    content
)
content = re.sub(
    r'type: \"\{\{ \'Equipment\' if item\.rental_price is defined else \'Service\' \}\}\"',
    'type: {{ item.display_type|tojson }}',
    content
)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Template updated!')
