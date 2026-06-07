import re

path = 'templates/caterer/services.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add max_stock_quantity input to Basic Info tab
target = """                        <div class="form-group-pro">
                            <!-- Empty spacer for layout -->
                        </div>"""
replacement = """                        <div class="form-group-pro">
                            <label>Max Stock Qty <i class="fas fa-boxes" title="Used for inventory logic. Leave empty for unlimited."></i></label>
                            <input type="number" name="max_stock_quantity" class="control-pro" placeholder="e.g. 50" min="0">
                        </div>"""
content = content.replace(target, replacement)

# 2. Update data attributes in edit button
target2 = """                        data-combo-options='{{ item.combo_options|tojson if item.combo_options else "[]" }}'
                        onclick="editMenuItem(this)">"""
replacement2 = """                        data-combo-options='{{ item.combo_options|tojson if item.combo_options else "[]" }}'
                        data-max-stock-quantity="{{ item.max_stock_quantity if item.max_stock_quantity is not none else '' }}"
                        onclick="editMenuItem(this)">"""
content = content.replace(target2, replacement2)

# 3. Update editMenuItem item object
target3 = """                is_combo: el.dataset.isCombo === 'true',
                max_choices: el.dataset.maxChoices || 0,
                combo_options: el.dataset.comboOptions || '[]'
            };"""
replacement3 = """                is_combo: el.dataset.isCombo === 'true',
                max_choices: el.dataset.maxChoices || 0,
                combo_options: el.dataset.comboOptions || '[]',
                max_stock_quantity: el.dataset.maxStockQuantity || ''
            };"""
content = content.replace(target3, replacement3)

# 4. Update editMenuItem form population
target4 = """            form.serving_size.value = item.serving_size || '';
            form.pricing_unit.value = item.pricing_unit || 'per_serving';"""
replacement4 = """            form.serving_size.value = item.serving_size || '';
            form.pricing_unit.value = item.pricing_unit || 'per_serving';
            if (form.max_stock_quantity) form.max_stock_quantity.value = item.max_stock_quantity || '';"""
content = content.replace(target4, replacement4)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched services.html!")
