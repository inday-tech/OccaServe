import re

path = 'templates/caterer/menu.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update global categories filter
target = """{% set categories_list = ['Appetizer', 'Soup', 'Salad', 'Main Course', 'Side Dish', 'Dessert', 'Drinks', 'Party Trays / Bilao', 'Other'] %}"""
replacement = """{% set categories_list = ['Appetizer', 'Soup', 'Salad', 'Main Course', 'Side Dish', 'Dessert', 'Drinks', 'Party Trays / Bilao', 'Rentals', 'Equipment', 'Other'] %}"""
content = content.replace(target, replacement)

# 2. Update dropdown modal options
target2 = """                                <option value="Party Trays / Bilao">Party Trays / Bilao</option>
                                <option value="Other">Other</option>"""
replacement2 = """                                <option value="Party Trays / Bilao">Party Trays / Bilao</option>
                                <option value="Rentals">Rentals</option>
                                <option value="Equipment">Equipment</option>
                                <option value="Other">Other</option>"""
content = content.replace(target2, replacement2)

# 3. Add ID to max_stock_quantity container and input
target3 = """                        <div class="form-group-pro">
                            <label>Max Stock Qty</label>
                            <input type="number" name="max_stock_quantity" class="control-pro" placeholder="e.g. 50" min="0">
                        </div>"""
replacement3 = """                        <div class="form-group-pro" id="stockQtyContainer" style="display: none;">
                            <label>Max Stock Qty</label>
                            <input type="number" name="max_stock_quantity" id="maxStockQuantityInput" class="control-pro" placeholder="e.g. 50" min="0">
                        </div>"""
content = content.replace(target3, replacement3)

# 4. Add logic to toggle stock quantity visibility
# We will append some JS at the end of the script tag.
js_to_add = """
    // Inventory Field Visibility Logic
    const categorySelect = document.getElementById('modalCategory');
    const stockContainer = document.getElementById('stockQtyContainer');
    
    function toggleStockVisibility() {
        if (!categorySelect || !stockContainer) return;
        const val = categorySelect.value.toLowerCase();
        if (val === 'rentals' || val === 'equipment' || val === 'services') {
            stockContainer.style.display = 'block';
        } else {
            stockContainer.style.display = 'none';
            document.getElementById('maxStockQuantityInput').value = '';
        }
    }
    
    if (categorySelect) {
        categorySelect.addEventListener('change', toggleStockVisibility);
    }
"""
target4 = """    const menuValidation = new window.ValidationManager"""
replacement4 = js_to_add + "\n    const menuValidation = new window.ValidationManager"
content = content.replace(target4, replacement4)

# 5. Call toggleStockVisibility on edit
target5 = """            form.max_stock_quantity.value = item.max_stock_quantity || '';"""
replacement5 = """            form.max_stock_quantity.value = item.max_stock_quantity || '';
            toggleStockVisibility();"""
content = content.replace(target5, replacement5)

# 6. Call toggleStockVisibility on openAddMenuModal
target6 = """        switchDishTab('basic');"""
replacement6 = """        switchDishTab('basic');
        toggleStockVisibility();"""
content = content.replace(target6, replacement6)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched menu.html dynamically!")
