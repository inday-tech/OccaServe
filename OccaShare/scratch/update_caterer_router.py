import codecs
import re

file_path = 'c:\\OccaServe\\OccaShare\\app\\routers\\caterer_dashboard.py'
with codecs.open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add min_order_qty to add_menu_item
add_search = 'serving_size = form_data.get("serving_size")'
add_replace = 'serving_size = form_data.get("serving_size")\n        min_order_qty = int(form_data.get("min_order_qty", "1") or "1")\n    else:\n        min_order_qty = 1'
content = content.replace(add_search, add_replace, 1)

add_kwargs = 'serving_size=serving_size,'
add_kwargs_replace = 'serving_size=serving_size,\n        min_order_qty=min_order_qty,'
content = content.replace(add_kwargs, add_kwargs_replace, 1)

# Add min_order_qty to update_menu_item
update_search = 'menu_item.serving_size = form_data.get("serving_size")'
update_replace = 'menu_item.serving_size = form_data.get("serving_size")\n            menu_item.min_order_qty = int(form_data.get("min_order_qty", "1") or "1")'
content = content.replace(update_search, update_replace, 1)

with codecs.open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
