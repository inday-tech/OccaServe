import re

html_path = r'c:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Jinja item.rental_price check
content = re.sub(
    r'\{% set item_price = \(item\.rental_price if item\.rental_price is defined else item\.selling_price\) or 0 %\}',
    '{% set item_price = (item.rental_price if item.__tablename__ == \'equipment\' else item.selling_price) or 0 %}',
    content
)

# Fix 2: JSON representation inside window.hubInventoryItems
content = re.sub(
    r'price: \{\{ \(item\.rental_price if item\.rental_price is defined else item\.selling_price\)\|tojson \}\},',
    'price: {{ (item.rental_price if item.__tablename__ == \'equipment\' else item.selling_price)|tojson }},',
    content
)

content = re.sub(
    r'type: \"\{\{ \'Equipment\' if item\.rental_price is defined else \'Service\' \}\}\"',
    'type: \"{{ \'Equipment\' if item.__tablename__ == \'equipment\' else \'Service\' }}\"',
    content
)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Template fixed!')
