import sys

file_path = r'c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace block 1 (add_menu_item)
target_1 = """    price = 0.0
    serving_size = None
    if not (usage_type == "package_only") and pricing_mode == "single":
        try:
            price = float(form_data.get("price", "0").replace(",", ""))
        except ValueError:
            price = 0.0
        serving_size = form_data.get("serving_size")
        min_order_qty = int(form_data.get("min_order_qty", "1") or "1")
    else:
        min_order_qty = 1"""

replace_1 = """    price = 0.0
    serving_size = None
    if not (usage_type == "package_only") and pricing_mode == "single":
        try:
            price = float(form_data.get("price", "0").replace(",", ""))
        except ValueError:
            price = 0.0
        serving_size = form_data.get("serving_size")

    if not (usage_type == "package_only"):
        min_order_qty = int(form_data.get("min_order_qty", "1") or "1")
    else:
        min_order_qty = 1"""

# Replace block 2 (update_menu_item)
target_2 = """    price = 0.0
    serving_size = None
    if not (usage_type == "package_only") and pricing_mode == "single":
        try:
            price = float(form_data.get("price", "0").replace(",", ""))
        except ValueError:
            price = 0.0
        serving_size = form_data.get("serving_size")
    
    is_hidden = form_data.get("visibility") == "hidden\""""

replace_2 = """    price = 0.0
    serving_size = None
    if not (usage_type == "package_only") and pricing_mode == "single":
        try:
            price = float(form_data.get("price", "0").replace(",", ""))
        except ValueError:
            price = 0.0
        serving_size = form_data.get("serving_size")

    if not (usage_type == "package_only"):
        min_order_qty = int(form_data.get("min_order_qty", "1") or "1")
    else:
        min_order_qty = 1
    
    is_hidden = form_data.get("visibility") == "hidden\""""

# Replace block 3 (update_menu_item save)
target_3 = """    item.name = name
    item.category = category
    item.description = description
    item.cost_price = cost_price
    item.price = price
    item.serving_size = serving_size
    item.status = status
    item.usage_type = usage_type
    item.available_for_package = available_for_package"""

replace_3 = """    item.name = name
    item.category = category
    item.description = description
    item.cost_price = cost_price
    item.price = price
    item.serving_size = serving_size
    item.min_order_qty = min_order_qty
    item.status = status
    item.usage_type = usage_type
    item.available_for_package = available_for_package"""

# Convert CRLF to LF for matching if needed
content = content.replace('\r\n', '\n')
target_1 = target_1.replace('\r\n', '\n')
replace_1 = replace_1.replace('\r\n', '\n')
target_2 = target_2.replace('\r\n', '\n')
replace_2 = replace_2.replace('\r\n', '\n')
target_3 = target_3.replace('\r\n', '\n')
replace_3 = replace_3.replace('\r\n', '\n')

content = content.replace(target_1, replace_1)
content = content.replace(target_2, replace_2)
content = content.replace(target_3, replace_3)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success')
