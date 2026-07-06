import re
import os

filepath = r'c:\OccaServe\OccaShare\templates\caterer\profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix opacity-0 hover issues so text/buttons are visible
content = content.replace('opacity-0 group-hover:opacity-100', 'opacity-100')
content = content.replace('group-hover:opacity-0', 'opacity-100')

# Update public-pkg-modal to be bigger and scrollable
content = content.replace(
    '<div class="relative bg-white w-full max-w-md rounded-2xl shadow-xl p-6 animate-in zoom-in-95 duration-300">',
    '<div class="relative bg-white w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-3xl shadow-2xl p-8 animate-in zoom-in-95 duration-300 border border-slate-100">'
)

# Add Caterer Scheduling Rules to JS
if 'const catererScheduling' not in content:
    content = content.replace(
        'const publicPortfoliosData = {',
        'const catererScheduling = {{ (caterer.scheduling_rules or {})|tojson }};\n    const publicPortfoliosData = {'
    )

# Update menuDishes with status and min_order_qty
if 'min_order_qty: ' not in content.split('const menuDishes = {')[1].split('const inventoryItems = {')[0]:
    menu_replacement = """                pricing_type: "{{ item.pricing_type or 'fixed' }}",
                status: {{ (item.status or 'available')|tojson }},
                min_order_qty: {{ (item.min_order_qty or 1)|tojson }},
                description: {{ item.description|default('', true)|tojson }},"""
    content = content.replace(
        '                pricing_type: "{{ item.pricing_type or \'fixed\' }}",\n                description: {{ item.description|default(\'\', true)|tojson }},',
        menu_replacement
    )

# Update inventoryItems with status
if 'status: ' not in content.split('const inventoryItems = {')[1]:
    inventory_replacement = """                type: "{{ 'Equipment' if item.rental_price is defined else 'Service' }}",
                status: {{ (item.status or 'available')|tojson }},
                description: {{ item.description|default('', true)|tojson }},"""
    content = content.replace(
        '                type: "{{ \'Equipment\' if item.rental_price is defined else \'Service\' }}",\n                description: {{ item.description|default(\'\', true)|tojson }},',
        inventory_replacement
    )

# Write back
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Initial patch applied successfully.")
