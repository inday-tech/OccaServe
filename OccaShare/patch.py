import re

path = 'templates/caterer/menu.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add data-max-stock-quantity
target = """data-combo-options='{{ item.combo_options|tojson if item.combo_options else "[]" }}'
                        onclick="editMenuItem(this)">"""
replacement = """data-combo-options='{{ item.combo_options|tojson if item.combo_options else "[]" }}'
                        data-max-stock-quantity="{{ item.max_stock_quantity if item.max_stock_quantity is not none else '' }}"
                        onclick="editMenuItem(this)">"""
content = content.replace(target, replacement)

# 2. Update editMenuItem item object
target2 = """                is_combo: el.dataset.isCombo === 'true',
                max_choices: el.dataset.maxChoices || 0,
                combo_options: el.dataset.comboOptions || '[]'
            };"""
replacement2 = """                is_combo: el.dataset.isCombo === 'true',
                max_choices: el.dataset.maxChoices || 0,
                combo_options: el.dataset.comboOptions || '[]',
                max_stock_quantity: el.dataset.maxStockQuantity || ''
            };"""
content = content.replace(target2, replacement2)

# 3. Update editMenuItem form population
target3 = """            form.serving_size.value = item.serving_size || '';
            form.pricing_unit.value = item.pricing_unit || 'per_serving';"""
replacement3 = """            form.serving_size.value = item.serving_size || '';
            form.pricing_unit.value = item.pricing_unit || 'per_serving';
            form.max_stock_quantity.value = item.max_stock_quantity || '';"""
content = content.replace(target3, replacement3)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched!")
