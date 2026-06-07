import re

path = 'templates/caterer/menu.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove max stock container
content = re.sub(
    r'<div class="form-group-pro" id="stockQtyContainer" style="display: none;">\s*<label>Max Stock Qty</label>\s*<input type="number" name="max_stock_quantity" id="maxStockQuantityInput" class="control-pro" placeholder="e.g. 50" min="0">\s*</div>',
    """<div class="form-group-pro">
                            <!-- Empty spacer for layout -->
                        </div>""",
    content
)

# Remove dynamic options
content = content.replace('<option value="Rentals">Rentals</option>', '')
content = content.replace('<option value="Equipment">Equipment</option>', '')
content = content.replace('<option value="Services">Services</option>', '')

# Remove JS
js_removal = """
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
content = content.replace(js_removal, "")

content = content.replace("toggleStockVisibility();", "")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Reverted menu.html!")
