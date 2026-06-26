import re
with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_js_price = '''        price: "₱{{ '{:,.2f}'.format(pkg.price_per_head if pkg.price_per_head else (pkg.price or 0)) }}{{ '/pax' if (pkg.price_per_head or pkg.price_unit == 'per_guest') else '' }}",'''
new_js_price = '''        price: "₱{{ '{:,.2f}'.format(pkg.price if pkg.price else (pkg.price_per_head if pkg.price_per_head else 0)) if pkg.price_unit == 'total' else '{:,.2f}'.format(pkg.price_per_head if pkg.price_per_head else (pkg.price if pkg.price else 0)) }}{{ ' total' if pkg.price_unit == 'total' else '/pax' }}",'''

content = content.replace(old_js_price, new_js_price)

with open(r'C:\OccaServe\OccaShare\templates\customer\caterer_profile_view.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed package pricing JS display")
