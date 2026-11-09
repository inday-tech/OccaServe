def calculate_event_estimate(event, package, menu_items, equipment_items, service_items):
    """Calculate an event estimate from the selected caterer's current catalog data."""
    guest_count = int(event["guest_count"])
    pricing_mode = (package.pricing_mode or ("per_pax" if package.price_unit == "per_guest" else "fixed")).lower()
    price_unit = (package.price_unit or "per_guest").lower()
    price_per_guest = float(package.price_per_head or package.price or 0)

    if pricing_mode == "fixed" or price_unit != "per_guest":
        package_total = float(package.price or package.price_per_head or 0)
        additional_guest_price = float(package.additional_guest_price or 0)
        package_total += max(guest_count - int(package.min_guests or 0), 0) * additional_guest_price
    else:
        package_total = price_per_guest * guest_count

    included_menu_ids = {item.id for item in package.menu_items or []}
    included_equipment_ids = {
        link.equipment_id for link in package.equipment_links or [] if link.equipment_id
    }
    included_service_ids = {
        link.service_id for link in package.service_links or [] if link.service_id
    }
    menu_addon_prices = {
        link.menu_item_id: float(link.price or 0)
        for link in package.menu_addons or []
        if link.is_enabled and link.menu_item_id
    }
    equipment_addon_prices = {
        link.equipment_id: float(link.price or 0)
        for link in package.equipment_addons or []
        if link.is_enabled and link.equipment_id
    }
    service_addon_prices = {
        link.service_id: float(link.price or 0)
        for link in package.service_addons or []
        if link.is_enabled and link.service_id
    }

    menu_total = 0.0
    for item in menu_items:
        if item.id in included_menu_ids:
            continue
        if item.is_addon:
            item_price = menu_addon_prices.get(item.id, float(item.addon_price or item.price or 0))
        elif pricing_mode == "customizable" and float(item.upgrade_fee or 0) > 0:
            item_price = float(item.upgrade_fee)
        else:
            item_price = float(item.price or item.upgrade_fee or 0)
        unit = str(item.pricing_unit or "").lower()
        menu_total += item_price * (guest_count if unit in {"per_pax", "per_guest", "per_person"} else 1)

    equipment_total = sum(
        equipment_addon_prices.get(item.id, float(item.addon_price or item.rental_price or 0))
        for item in equipment_items
        if item.id not in included_equipment_ids
    )
    service_total = sum(
        service_addon_prices.get(item.id, float(item.addon_price or item.selling_price or 0))
        * (guest_count if str(item.unit_type or "").lower() in {"per_pax", "per_guest", "per_person"} else 1)
        for item in service_items
        if item.id not in included_service_ids
    )

    subtotal = round(package_total + menu_total + equipment_total + service_total, 2)
    return {
        "package": round(package_total, 2),
        "menu": round(menu_total, 2),
        "equipment": round(equipment_total, 2),
        "services": round(service_total, 2),
        "subtotal": subtotal,
    }
