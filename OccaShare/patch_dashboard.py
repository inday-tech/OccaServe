import re

path = 'app/routers/caterer_dashboard.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update update_business_profile for Caterer settings
target = """    booking_lead_time: Optional[int] = Form(7),
    min_pax: Optional[int] = Form(20),"""
replacement = """    booking_lead_time: Optional[int] = Form(7),
    equipment_turnover_hours: Optional[int] = Form(24),
    min_pax: Optional[int] = Form(20),"""
content = content.replace(target, replacement)

target2 = """    profile.booking_lead_time = booking_lead_time
    profile.min_pax = min_pax"""
replacement2 = """    profile.booking_lead_time = booking_lead_time
    profile.equipment_turnover_hours = equipment_turnover_hours
    profile.min_pax = min_pax"""
content = content.replace(target2, replacement2)

# 2. Update add_menu_item
target3 = """    serving_size: Optional[str] = Form(None),
    pricing_unit: str = Form("per_serving"),"""
replacement3 = """    serving_size: Optional[str] = Form(None),
    max_stock_quantity: Optional[int] = Form(None),
    pricing_unit: str = Form("per_serving"),"""
content = content.replace(target3, replacement3)

target4 = """        serving_size=serving_size,
        pricing_unit=pricing_unit,"""
replacement4 = """        serving_size=serving_size,
        max_stock_quantity=max_stock_quantity,
        pricing_unit=pricing_unit,"""
content = content.replace(target4, replacement4)

# 3. Update update_menu_item
target5 = """    serving_size: Optional[str] = Form(None),
    pricing_unit: str = Form("per_serving"),"""
replacement5 = """    serving_size: Optional[str] = Form(None),
    max_stock_quantity: Optional[int] = Form(None),
    pricing_unit: str = Form("per_serving"),"""
content = content.replace(target5, replacement5)

target6 = """    item.serving_size = serving_size
    item.pricing_unit = pricing_unit"""
replacement6 = """    item.serving_size = serving_size
    item.max_stock_quantity = max_stock_quantity
    item.pricing_unit = pricing_unit"""
content = content.replace(target6, replacement6)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched caterer_dashboard.py!")
