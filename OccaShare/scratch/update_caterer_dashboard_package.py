import re

file_path = r"c:\OccaServe\OccaShare\app\routers\caterer_dashboard.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace add_package definition
old_add_package_def = """async def add_package(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    pricing_mode: str = Form("per_pax"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[int] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[str]] = Form(None),
    additional_guest_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    transportation_cost: float = Form(0.0),
    miscellaneous_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    reservation_fee_type: str = Form("fixed"),
    reservation_fee_value: float = Form(0.0),
    booking_lead_time: int = Form(7),
    selection_rules: Optional[str] = Form(None),"""

new_add_package_def = """async def add_package(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    pricing_mode: str = Form("per_pax"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[int] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[str]] = Form(None),
    additional_guest_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    transportation_cost: float = Form(0.0),
    miscellaneous_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    reservation_fee_type: str = Form("fixed"),
    reservation_fee_value: float = Form(0.0),
    booking_lead_time: int = Form(7),
    selection_rules: Optional[str] = Form(None),
    status: str = Form("active"),
    policies_cancellation: Optional[str] = Form(None),
    policies_internal: Optional[str] = Form(None),"""

content = content.replace(old_add_package_def, new_add_package_def)

old_update_package_def = """async def update_package(
    request: Request,
    package_id: int,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    pricing_mode: str = Form("per_pax"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[int] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[str]] = Form(None),
    additional_guest_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    transportation_cost: float = Form(0.0),
    miscellaneous_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    reservation_fee_type: str = Form("fixed"),
    reservation_fee_value: float = Form(0.0),
    booking_lead_time: int = Form(7),
    selection_rules: Optional[str] = Form(None),"""

new_update_package_def = """async def update_package(
    request: Request,
    package_id: int,
    name: str = Form(...),
    description: str = Form(...),
    service_type: str = Form("General"),
    pricing_mode: str = Form("per_pax"),
    service_duration: int = Form(8),
    price_per_head: float = Form(0.0),
    cost_price: float = Form(0.0),
    cost_breakdown: Optional[str] = Form(None),
    markup_type: str = Form("percentage"),
    markup_value: float = Form(0.0),
    min_contract_amount: float = Form(0.0),
    min_guests: int = Form(1),
    max_guests: Optional[int] = Form(None),
    inclusions: Optional[List[str]] = Form(None),
    linked_menu_ids: Optional[List[str]] = Form(None),
    additional_guest_price: float = Form(0.0),
    image: Optional[UploadFile] = File(None),
    base_pax: int = Form(50),
    labor_cost: float = Form(0.0),
    utility_cost: float = Form(0.0),
    equipment_cost: float = Form(0.0),
    transportation_cost: float = Form(0.0),
    miscellaneous_cost: float = Form(0.0),
    internal_cost_per_pax: float = Form(0.0),
    reservation_fee_type: str = Form("fixed"),
    reservation_fee_value: float = Form(0.0),
    booking_lead_time: int = Form(7),
    selection_rules: Optional[str] = Form(None),
    status: str = Form("active"),
    policies_cancellation: Optional[str] = Form(None),
    policies_internal: Optional[str] = Form(None),"""

content = content.replace(old_update_package_def, new_update_package_def)

# Remove the internal_cost_per_pax check in BOTH add and update
internal_cost_check = """    if price_per_head < internal_cost_per_pax:
        errors.append(f"Selling Price cannot be lower than the Est. Cost / Pax.")"""
content = content.replace(internal_cost_check, "")


old_add_package_model = """        booking_lead_time=booking_lead_time,
        selection_rules=json.loads(selection_rules) if selection_rules else None,
        is_active=True,
        status='active'
    )"""

new_add_package_model = """        booking_lead_time=booking_lead_time,
        selection_rules=json.loads(selection_rules) if selection_rules else None,
        policies={"cancellation": policies_cancellation, "internal": policies_internal},
        is_active=status == 'active',
        status=status
    )"""

content = content.replace(old_add_package_model, new_add_package_model)


old_update_package_model = """    package.selection_rules = json.loads(selection_rules) if selection_rules else None
    
    # Handle optional image update
    import base64"""

new_update_package_model = """    package.selection_rules = json.loads(selection_rules) if selection_rules else None
    package.policies = {"cancellation": policies_cancellation, "internal": policies_internal}
    package.status = status
    package.is_active = status == 'active'
    
    # Handle optional image update
    import base64"""

content = content.replace(old_update_package_model, new_update_package_model)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Backend update complete.")
