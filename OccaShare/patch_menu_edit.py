import os

path = 'templates/caterer/menu.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove max_stock_quantity from the item object
content = content.replace("combo_options: el.dataset.comboOptions || '[]',", "combo_options: el.dataset.comboOptions || '[]'")
content = content.replace("max_stock_quantity: el.dataset.maxStockQuantity || ''\n            };", "            };")

# 2. Remove the form assignment
content = content.replace("form.max_stock_quantity.value = item.max_stock_quantity || '';\n", "")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Menu edit logic fixed!")
