from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


class PackagePricingError(ValueError):
    pass


def _amount(value: Any, label: str) -> Decimal:
    try:
        amount = Decimal(str(value if value is not None else 0))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise PackagePricingError(f"{label} must be a valid amount.") from exc
    if not amount.is_finite() or amount < 0:
        raise PackagePricingError(f"{label} cannot be negative or invalid.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ids(items: Any, label: str) -> list[int]:
    if not isinstance(items, list):
        raise PackagePricingError(f"Selected {label} must be a list.")
    result = []
    for item in items:
        raw_id = item.get("id") if isinstance(item, dict) else item
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise PackagePricingError(f"Selected {label} contains an invalid item.") from exc
        if item_id < 1:
            raise PackagePricingError(f"Selected {label} contains an invalid item.")
        if item_id in result:
            raise PackagePricingError(f"The same {label} cannot be selected more than once.")
        result.append(item_id)
    return result


def _rules_for(package: Any) -> dict:
    rules = getattr(package, "selection_rules", None) or {}
    if isinstance(rules, str):
        import json
        try:
            rules = json.loads(rules)
        except json.JSONDecodeError as exc:
            raise PackagePricingError("This package has invalid customization settings. Please contact the caterer.") from exc
    if not isinstance(rules, dict):
        raise PackagePricingError("This package has invalid customization settings. Please contact the caterer.")
    return rules


def _configured_ids(rules: dict, key: str) -> set[int]:
    values = rules.get(key, [])
    if not isinstance(values, list):
        raise PackagePricingError("This package has invalid customization settings. Please contact the caterer.")
    try:
        return {int(value) for value in values if int(value) > 0}
    except (TypeError, ValueError) as exc:
        raise PackagePricingError("This package has invalid customization settings. Please contact the caterer.") from exc


def _menu_extra_options(rules: dict) -> dict[int, dict[str, Any]]:
    raw_options = rules.get("menu_extra_options", {})
    if not isinstance(raw_options, dict):
        raise PackagePricingError("This package has invalid extra-dish settings.")
    options = {}
    for raw_id, raw_config in raw_options.items():
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise PackagePricingError("This package has invalid extra-dish settings.") from exc
        if item_id < 1 or not isinstance(raw_config, dict):
            raise PackagePricingError("This package has invalid extra-dish settings.")
        raw_variants = raw_config.get("variants")
        if raw_variants is None:
            raw_variants = [{"size": "Standard serving", "price": raw_config.get("price")}]
        if not isinstance(raw_variants, list) or not raw_variants:
            raise PackagePricingError("Each extra dish must have at least one size and price.")
        variants = []
        used_sizes = set()
        for variant in raw_variants:
            if not isinstance(variant, dict):
                raise PackagePricingError("Extra-dish sizes must include a size name and price.")
            size = str(variant.get("size") or "").strip()
            if not size or len(size) > 80 or size.casefold() in used_sizes:
                raise PackagePricingError("Each extra-dish size must have a unique name of 1 to 80 characters.")
            price = _amount(variant.get("price"), "Extra-dish price")
            if price <= 0 or price > Decimal("99999999.99"):
                raise PackagePricingError("Extra-dish prices must be greater than ₱0 and no more than ₱99,999,999.99.")
            used_sizes.add(size.casefold())
            variants.append({"size": size, "price": price})
        try:
            raw_max_quantity = raw_config.get("max_quantity", 999)
            max_quantity = int(raw_max_quantity)
            if isinstance(raw_max_quantity, bool) or Decimal(str(raw_max_quantity)) != Decimal(max_quantity):
                raise ValueError
        except (InvalidOperation, OverflowError, TypeError, ValueError) as exc:
            raise PackagePricingError("This package has invalid extra-dish quantity limits.") from exc
        if not 1 <= max_quantity <= 999:
            raise PackagePricingError("Extra-dish quantity limits must be between 1 and 999.")
        options[item_id] = {
            "price": variants[0]["price"],
            "variants": variants,
            "max_quantity": max_quantity,
        }
    return options


def validate_customizable_menu_extra_options(rules: Any) -> dict[int, dict[str, Any]]:
    if not isinstance(rules, dict):
        raise PackagePricingError("Customizable package settings must be a valid object.")
    options = _menu_extra_options(rules)
    allowed_menu = _configured_ids(rules, "available_menu_ids")
    if not set(options).issubset(allowed_menu):
        raise PackagePricingError("Extra dishes must be selected in this package's available menu.")
    return options


def _menu_replacement_rules(rules: dict) -> tuple[set[int], dict[int, dict[int, Decimal]]]:
    included_ids = _configured_ids(rules, "included_menu_ids")
    raw_replacements = rules.get("menu_replacements", {})
    if not isinstance(raw_replacements, dict):
        raise PackagePricingError("This package has invalid menu replacement settings.")
    replacements: dict[int, dict[int, Decimal]] = {}
    for raw_included_id, raw_options in raw_replacements.items():
        try:
            included_id = int(raw_included_id)
        except (TypeError, ValueError) as exc:
            raise PackagePricingError("This package has invalid menu replacement settings.") from exc
        if included_id not in included_ids or not isinstance(raw_options, dict):
            raise PackagePricingError("Menu replacements must be configured for included package dishes.")
        options = {}
        for raw_option_id, raw_fee in raw_options.items():
            try:
                option_id = int(raw_option_id)
            except (TypeError, ValueError) as exc:
                raise PackagePricingError("This package has an invalid replacement item.") from exc
            fee = _amount(raw_fee, "Menu replacement fee")
            if option_id < 1 or option_id == included_id or fee < 0:
                raise PackagePricingError("Menu replacements must have a valid item and an explicit fee of at least ₱0.")
            if fee > Decimal("99999999.99"):
                raise PackagePricingError("Menu replacement fees cannot exceed ₱99,999,999.99.")
            options[option_id] = fee
        replacements[included_id] = options
    return included_ids, replacements


def _price_overrides(rules: dict, key: str, allowed_ids: set[int], label: str) -> dict[int, Decimal]:
    raw_prices = rules.get(key, {})
    if not isinstance(raw_prices, dict):
        raise PackagePricingError(f"This package has invalid {label} prices.")
    prices = {}
    for raw_id, raw_price in raw_prices.items():
        try:
            item_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise PackagePricingError(f"This package has an invalid {label} item.") from exc
        price = _amount(raw_price, f"{label} package price")
        if item_id not in allowed_ids or price <= 0 or price > Decimal("99999999.99"):
            raise PackagePricingError(f"{label} package prices must be valid and belong to available package items.")
        prices[item_id] = price
    return prices


def _equipment_quantity_limits(rules: dict, allowed_ids: set[int]) -> dict[int, int]:
    raw_limits = rules.get("equipment_quantity_limits", {})
    if not isinstance(raw_limits, dict):
        raise PackagePricingError("This package has invalid equipment quantity limits.")
    limits = {}
    for raw_id, raw_limit in raw_limits.items():
        try:
            item_id = int(raw_id)
            limit = int(raw_limit)
            if isinstance(raw_limit, bool) or Decimal(str(raw_limit)) != Decimal(limit):
                raise ValueError
        except (InvalidOperation, OverflowError, TypeError, ValueError) as exc:
            raise PackagePricingError("This package has invalid equipment quantity limits.") from exc
        if item_id not in allowed_ids or not 1 <= limit <= 9999:
            raise PackagePricingError("Equipment quantity limits must be between 1 and 9,999.")
        limits[item_id] = limit
    return limits


def validate_customizable_addon_rules(rules: Any) -> None:
    if not isinstance(rules, dict):
        raise PackagePricingError("Customizable package settings must be a valid object.")
    service_ids = _configured_ids(rules, "available_service_ids")
    equipment_ids = _configured_ids(rules, "available_equipment_ids")
    included_services = _configured_ids(rules, "included_service_ids")
    included_equipment = _configured_ids(rules, "included_equipment_ids")
    if not included_services.issubset(service_ids) or not included_equipment.issubset(equipment_ids):
        raise PackagePricingError("Included services and equipment must be selected in this package.")
    _price_overrides(rules, "service_prices", service_ids, "Service")
    _price_overrides(rules, "equipment_prices", equipment_ids, "Equipment")
    _equipment_quantity_limits(rules, equipment_ids)


def validate_customizable_menu_rules(rules: Any, menu_items: dict[int, Any]) -> None:
    if not isinstance(rules, dict):
        raise PackagePricingError("Customizable package settings must be a valid object.")
    extra_options = validate_customizable_menu_extra_options(rules)
    available_ids = _configured_ids(rules, "available_menu_ids")
    if not set(extra_options).issubset(available_ids):
        raise PackagePricingError("Extra dishes must be selected in this package's available menu.")
    if "included_menu_ids" not in rules:
        return
    included_ids, replacements = _menu_replacement_rules(rules)
    if not included_ids.issubset(available_ids) or not included_ids.issubset(menu_items):
        raise PackagePricingError("Included default dishes must be selected and available in this package.")
    if available_ids and not included_ids:
        raise PackagePricingError("Select at least one included default dish for the customizable menu slots.")
    quotas = rules.get("category_quotas", {})
    if not isinstance(quotas, dict):
        raise PackagePricingError("This package has invalid menu selection limits.")
    available_by_category: dict[str, set[int]] = {}
    defaults_by_category: dict[str, set[int]] = {}
    for item_id in available_ids:
        if item_id not in menu_items:
            continue
        category = (getattr(menu_items[item_id], "category", None) or "Others").strip()
        available_by_category.setdefault(category, set()).add(item_id)
        if item_id in included_ids:
            defaults_by_category.setdefault(category, set()).add(item_id)
    for category, category_items in available_by_category.items():
        default_count = len(defaults_by_category.get(category, set()))
        if default_count == 0:
            continue
        try:
            quota = int(quotas.get(category))
        except (TypeError, ValueError) as exc:
            raise PackagePricingError(f"Set a valid menu slot count for {category}.") from exc
        if not 1 <= quota <= len(category_items) or default_count != quota:
            raise PackagePricingError(
                f"Choose exactly {quota} included default dish(es) for the {category} menu slots."
            )
    for included_id, options in replacements.items():
        for option_id in options:
            if option_id not in available_ids or option_id not in menu_items or option_id in included_ids:
                raise PackagePricingError("Replacement dishes must be selected and available in this package.")
            if not getattr(menu_items[option_id], "status", "available") == "available":
                raise PackagePricingError("Replacement dishes must be available in this package.")


def calculate_customization(
    package: Any,
    payload: Any,
    menu_items: dict[int, Any],
    services: dict[int, Any],
    equipment: dict[int, Any],
    service_price_overrides: dict[int, Any] | None = None,
    equipment_price_overrides: dict[int, Any] | None = None,
) -> dict:
    """Rebuild a customer estimate using package rules and trusted catalog records."""
    if not isinstance(payload, dict):
        raise PackagePricingError("Customization details are invalid.")
    rules = _rules_for(package)

    try:
        guest_count = int(payload.get("guest_count"))
    except (TypeError, ValueError) as exc:
        raise PackagePricingError("Enter a valid guest count.") from exc
    minimum = max(1, int(getattr(package, "min_guests", 1) or 1))
    maximum = getattr(package, "max_guests", None)
    if guest_count < minimum:
        raise PackagePricingError(f"This package requires at least {minimum} guests.")
    if maximum is not None and guest_count > int(maximum):
        raise PackagePricingError(f"This package allows at most {int(maximum)} guests.")

    menu_ids = _ids(payload.get("selected_food", []), "menu item")
    service_ids = _ids(payload.get("selected_services", []), "service")
    raw_equipment = payload.get("selected_equipment", [])
    equipment_ids = _ids(raw_equipment, "equipment item")
    equipment_quantities = {}
    for row in raw_equipment:
        if not isinstance(row, dict):
            continue
        try:
            item_id = int(row.get("id"))
            raw_quantity = row.get("qty", 1)
            quantity = int(raw_quantity)
            if isinstance(raw_quantity, bool) or Decimal(str(raw_quantity)) != Decimal(quantity):
                raise ValueError
        except (InvalidOperation, OverflowError, TypeError, ValueError) as exc:
            raise PackagePricingError("Selected equipment contains an invalid quantity.") from exc
        equipment_quantities[item_id] = quantity
    raw_extras = payload.get("selected_menu_extras", [])
    if not isinstance(raw_extras, list):
        raise PackagePricingError("Selected extra dishes must be a list.")
    extra_quantities: dict[int, int] = {}
    for extra in raw_extras:
        if not isinstance(extra, dict):
            raise PackagePricingError("Selected extra dishes contain an invalid item.")
        try:
            item_id = int(extra.get("id"))
            raw_quantity = extra.get("qty", 1)
            quantity = int(raw_quantity)
            if isinstance(raw_quantity, bool) or Decimal(str(raw_quantity)) != Decimal(quantity):
                raise ValueError
        except (InvalidOperation, OverflowError, TypeError, ValueError) as exc:
            raise PackagePricingError("Selected extra dishes contain an invalid item or quantity.") from exc
        if item_id < 1 or item_id in extra_quantities:
            raise PackagePricingError("The same extra dish cannot be listed more than once.")
        extra_quantities[item_id] = quantity

    extra_options = _menu_extra_options(rules)
    validate_customizable_addon_rules(rules)
    allowed_menu = _configured_ids(rules, "available_menu_ids")
    allowed_services = _configured_ids(rules, "available_service_ids")
    allowed_equipment = _configured_ids(rules, "available_equipment_ids")
    included_service_ids = _configured_ids(rules, "included_service_ids")
    included_equipment_ids = _configured_ids(rules, "included_equipment_ids")
    service_ids = list(dict.fromkeys(service_ids + sorted(included_service_ids)))
    equipment_ids = list(dict.fromkeys(equipment_ids + sorted(included_equipment_ids)))
    validate_customizable_menu_rules(rules, menu_items)
    configured_menu_slots = "included_menu_ids" in rules
    included_menu_ids, replacement_options = (
        _menu_replacement_rules(rules) if configured_menu_slots else (set(), {})
    )
    for item_id in menu_ids:
        if item_id not in allowed_menu or item_id not in menu_items:
            raise PackagePricingError("A selected menu item is no longer available for this package.")
    for item_id in service_ids:
        if item_id not in allowed_services or item_id not in services:
            raise PackagePricingError("A selected service is no longer available for this package.")
    for item_id in equipment_ids:
        if item_id not in allowed_equipment or item_id not in equipment:
            raise PackagePricingError("A selected equipment item is no longer available for this package.")
    configured_service_prices = _price_overrides(rules, "service_prices", allowed_services, "Service")
    configured_equipment_prices = _price_overrides(rules, "equipment_prices", allowed_equipment, "Equipment")
    equipment_limits = _equipment_quantity_limits(rules, allowed_equipment)
    for item_id, quantity in extra_quantities.items():
        if item_id not in extra_options or item_id not in allowed_menu or item_id not in menu_items:
            raise PackagePricingError("A selected extra dish is no longer available for this package.")
        if not 1 <= quantity <= extra_options[item_id]["max_quantity"]:
            raise PackagePricingError(f"{menu_items[item_id].name} quantity must be between 1 and {extra_options[item_id]['max_quantity']}.")

    category_quotas = rules.get("category_quotas", {})
    if not isinstance(category_quotas, dict):
        raise PackagePricingError("This package has invalid menu selection limits.")
    configured_menu_slots = "included_menu_ids" in rules
    menu_counts: dict[str, int] = {}
    for item_id in menu_ids:
        item = menu_items[item_id]
        category = (getattr(item, "category", None) or "Others").strip()
        menu_counts[category] = menu_counts.get(category, 0) + 1
    if not configured_menu_slots:
        for category, count in menu_counts.items():
            try:
                quota = max(1, int(category_quotas.get(category, 1)))
            except (TypeError, ValueError) as exc:
                raise PackagePricingError(f"This package has an invalid selection limit for {category}.") from exc
            if count > quota:
                raise PackagePricingError(f"Choose no more than {quota} item(s) in {category}.")

    replacement_fees: dict[int, dict[str, Any]] = {}
    if configured_menu_slots:
        requested_removed_early = payload.get("removed_categories", [])
        if not isinstance(requested_removed_early, list):
            raise PackagePricingError("Removed menu categories are invalid.")
        removed_categories_early = {
            str(category).strip() for category in requested_removed_early if str(category).strip()
        }
        available_defaults = included_menu_ids & allowed_menu & menu_items.keys()
        defaults_by_category: dict[str, list[int]] = {}
        for item_id in available_defaults:
            category = (getattr(menu_items[item_id], "category", None) or "Others").strip()
            defaults_by_category.setdefault(category, []).append(item_id)
        removed_default_ids = {
            item_id for category, ids in defaults_by_category.items()
            if category in removed_categories_early
            for item_id in ids
        }
        selected_menu_ids = set(menu_ids)
        selected_default_ids = selected_menu_ids & available_defaults
        if selected_default_ids & removed_default_ids:
            raise PackagePricingError("Remove the selected included dish before removing its category.")

        unmatched_defaults = available_defaults - selected_default_ids - removed_default_ids
        selected_replacements = selected_menu_ids - available_defaults
        for replacement_id in sorted(selected_replacements):
            eligible_defaults = sorted(
                default_id for default_id in unmatched_defaults
                if replacement_id in replacement_options.get(default_id, {})
            )
            if not eligible_defaults:
                raise PackagePricingError(
                    f"{menu_items[replacement_id].name} is not an approved replacement for an available package dish."
                )
            replaced_default = eligible_defaults[0]
            unmatched_defaults.remove(replaced_default)
            replacement_fees[replacement_id] = {
                "fee": replacement_options[replaced_default][replacement_id],
                "replacement_for": replaced_default,
            }
        if unmatched_defaults:
            missing_categories = sorted({
                (getattr(menu_items[item_id], "category", None) or "Others").strip()
                for item_id in unmatched_defaults
            })
            category = missing_categories[0]
            raise PackagePricingError(
                f"Choose the included {category} dish or an approved replacement, or remove that category."
            )

    base_price = _amount(
        getattr(package, "price_per_head", None) or getattr(package, "price", None),
        "Package price",
    )
    if base_price == 0:
        raise PackagePricingError("This package has no configured customer price. Ask the caterer to review it.")
    base_total = base_price if getattr(package, "pricing_mode", "") == "fixed" else base_price * guest_count
    normalized_food = []
    food_total = Decimal("0.00")
    for item_id in menu_ids:
        item = menu_items[item_id]
        if configured_menu_slots and item_id in included_menu_ids:
            price = Decimal("0.00")
            replacement_for = None
        elif configured_menu_slots:
            replacement = replacement_fees.get(item_id)
            if replacement is None:
                raise PackagePricingError(f"{item.name} is not an allowed replacement for an included package dish.")
            price = replacement["fee"]
            replacement_for = replacement["replacement_for"]
        else:
            price = _amount(getattr(item, "upgrade_fee", 0), f"{item.name} upgrade fee")
            replacement_for = None
        subtotal = price * guest_count
        food_total += subtotal
        normalized_food.append({
            "id": item_id,
            "name": item.name,
            "category": getattr(item, "category", None) or "Others",
            "upgrade_fee": float(price),
            "replacement_for": replacement_for,
            "replacement_for_name": (
                menu_items[replacement_for].name if replacement_for is not None else None
            ),
            "price": float(price),
            "unit": "pax",
            "qty": guest_count,
            "subtotal": float(subtotal),
        })

    normalized_extras = []
    extras_total = Decimal("0.00")
    for item_id, quantity in extra_quantities.items():
        item = menu_items[item_id]
        configured_extra = extra_options[item_id]
        requested_extra = next(
            row for row in raw_extras if int(row["id"]) == item_id
        )
        requested_size = str(requested_extra.get("size") or "").strip()
        variants = configured_extra["variants"]
        selected_variant = next(
            (variant for variant in variants if variant["size"].casefold() == requested_size.casefold()),
            None,
        )
        if selected_variant is None:
            if len(variants) == 1 and not requested_size:
                selected_variant = variants[0]
            else:
                raise PackagePricingError(f"Choose an available size for {item.name}.")
        unit_price = selected_variant["price"]
        subtotal = unit_price * quantity
        extras_total += subtotal
        normalized_extras.append({
            "id": item_id,
            "name": item.name,
            "category": getattr(item, "category", None) or "Others",
            "price": float(unit_price),
            "size": selected_variant["size"],
            "unit": "tray",
            "qty": quantity,
            "subtotal": float(subtotal),
        })

    service_overrides = dict(service_price_overrides or {})
    service_overrides.update(configured_service_prices)
    normalized_services = []
    services_total = Decimal("0.00")
    for item_id in service_ids:
        item = services[item_id]
        unit = (getattr(item, "unit_type", None) or "per_event").lower()
        if item_id in included_service_ids:
            unit_price = Decimal("0.00")
        elif item_id in service_overrides:
            unit_price = _amount(service_overrides[item_id], f"{item.name} package price")
        else:
            unit_price = _amount(getattr(item, "selling_price", 0), f"{item.name} price")
        if unit_price == 0 and item_id not in included_service_ids:
            raise PackagePricingError(f"{item.name} has no configured customer price. Ask the caterer to review this request.")
        if "pax" in unit or "guest" in unit or "person" in unit:
            quantity = guest_count
        elif "hour" in unit:
            quantity = max(
                int(getattr(item, "minimum_hours", 1) or 1),
                int(getattr(package, "service_duration", 1) or 1),
            )
        elif "staff" in unit or getattr(item, "capacity_type", "unit_based") == "staff_based":
            ratio = int(getattr(item, "staff_to_pax_ratio", 0) or 0)
            quantity = max(int(getattr(item, "min_staff_required", 1) or 1), (guest_count + ratio - 1) // ratio) if ratio > 0 else 1
        else:
            quantity = 1
        ratio = int(getattr(item, "staff_to_pax_ratio", 0) or 0)
        capacity_quantity = (
            max(int(getattr(item, "min_staff_required", 1) or 1), (guest_count + ratio - 1) // ratio)
            if getattr(item, "capacity_type", "unit_based") == "staff_based" and ratio > 0
            else 1
        )
        subtotal = unit_price * quantity
        services_total += subtotal
        normalized_services.append({
            "id": item_id,
            "name": item.name,
            "category": getattr(item, "category", None) or "Service",
            "price": float(unit_price),
            "unit": unit,
            "qty": quantity,
            "capacity_type": getattr(item, "capacity_type", "unit_based"),
            "staff_ratio": int(getattr(item, "staff_to_pax_ratio", 0) or 0),
            "min_staff": int(getattr(item, "min_staff_required", 1) or 1),
            "capacity_qty": capacity_quantity,
            "subtotal": float(subtotal),
            "included": item_id in included_service_ids,
        })

    equipment_overrides = equipment_price_overrides or {}
    equipment_overrides = dict(equipment_overrides)
    equipment_overrides.update(configured_equipment_prices)
    normalized_equipment = []
    equipment_total = Decimal("0.00")
    for item_id in equipment_ids:
        item = equipment[item_id]
        included = item_id in included_equipment_ids
        equipment_unit = (getattr(item, "unit_type", None) or "piece").lower()
        unit_price = Decimal("0.00") if included else _amount(
            equipment_overrides.get(item_id, getattr(item, "addon_price", None) or getattr(item, "rental_price", 0)),
            f"{item.name} rental price",
        )
        if unit_price == 0 and not included:
            raise PackagePricingError(f"{item.name} has no configured rental price. Ask the caterer to review this request.")
        quantity = 1 if included else equipment_quantities.get(item_id, 1)
        max_quantity = min(
            int(getattr(item, "available_qty", 0) or 0),
            equipment_limits.get(item_id, int(getattr(item, "available_qty", 0) or 0)),
        )
        if not 1 <= quantity <= max_quantity:
            raise PackagePricingError(f"{item.name} is currently unavailable.")
        duration_hours = max(1, int(getattr(package, "service_duration", 1) or 1))
        if "hour" in equipment_unit:
            duration_quantity = duration_hours
        elif "day" in equipment_unit:
            duration_quantity = (duration_hours + 23) // 24
        else:
            duration_quantity = 1
        subtotal = unit_price * quantity * duration_quantity
        equipment_total += subtotal
        normalized_equipment.append({
            "id": item_id,
            "name": item.name,
            "price": float(unit_price),
            "unit": equipment_unit,
            "qty": quantity,
            "duration_qty": duration_quantity,
            "subtotal": float(subtotal),
            "included": included,
        })

    configured_categories = {
        (getattr(menu_items[item_id], "category", None) or "Others").strip()
        for item_id in allowed_menu if item_id in menu_items
    }
    requested_removed = payload.get("removed_categories", [])
    if not isinstance(requested_removed, list):
        raise PackagePricingError("Removed menu categories are invalid.")
    removed = {str(category).strip() for category in requested_removed if str(category).strip()}
    if not removed.issubset(configured_categories):
        raise PackagePricingError("A removed menu category is not part of this package.")
    for category in removed:
        extra_selected = any(
            (getattr(menu_items[item_id], "category", None) or "Others").strip() == category
            for item_id in extra_quantities
        )
        selected_default_in_category = configured_menu_slots and any(
            item_id in included_menu_ids
            and (getattr(menu_items[item_id], "category", None) or "Others").strip() == category
            for item_id in menu_ids
        )
        if (not configured_menu_slots and menu_counts.get(category, 0)) or selected_default_in_category or extra_selected:
            raise PackagePricingError(f"Remove the selected {category} item before removing that category.")

    removal_credits = rules.get("category_removal_credits", {})
    if not isinstance(removal_credits, dict):
        raise PackagePricingError("This package has invalid removal-credit settings.")
    removal_total = Decimal("0.00")
    for category in removed:
        credit = _amount(removal_credits.get(category, 0), f"{category} removal credit")
        removal_total += credit * guest_count

    estimate = max(Decimal("0.00"), base_total + food_total + extras_total + services_total + equipment_total - removal_total)
    special_requests = str(payload.get("special_requests") or "").strip()[:4000]
    return {
        "package_id": int(package.id),
        "package_name": str(package.name),
        "pricing_mode": "customizable",
        "guest_count": guest_count,
        "base_price": float(base_price),
        "base_package_total": float(base_total),
        "food_upgrade_total": float(food_total),
        "food_removal_credit": float(removal_total),
        "removed_categories": sorted(removed),
        "selected_food": normalized_food,
        "selected_menu_extras": normalized_extras,
        "menu_extras_total": float(extras_total),
        "selected_services": normalized_services,
        "selected_equipment": normalized_equipment,
        "food_total": float(food_total),
        "services_total": float(services_total),
        "equipment_total": float(equipment_total),
        "estimated_total": float(estimate),
        "special_requests": special_requests,
    }


def load_and_calculate_customization(db: Any, package: Any, payload: Any) -> dict:
    from ..db import models

    rules = _rules_for(package)
    menu_ids = _ids(payload.get("selected_food", []) if isinstance(payload, dict) else [], "menu item")
    extra_rows = payload.get("selected_menu_extras", []) if isinstance(payload, dict) else []
    if not isinstance(extra_rows, list):
        raise PackagePricingError("Selected extra dishes must be a list.")
    extra_ids = _ids(
        [{"id": row.get("id")} for row in extra_rows if isinstance(row, dict)],
        "extra dish",
    )
    available_menu_ids = _configured_ids(rules, "available_menu_ids")
    included_ids = _configured_ids(rules, "included_menu_ids")
    _, replacement_rules = _menu_replacement_rules(rules) if "included_menu_ids" in rules else (set(), {})
    replacement_ids = {
        option_id for options in replacement_rules.values() for option_id in options
    }
    menu_ids = list(dict.fromkeys(
        menu_ids + extra_ids + list(available_menu_ids) + list(included_ids) + list(replacement_ids)
    ))
    service_ids = _ids(payload.get("selected_services", []) if isinstance(payload, dict) else [], "service")
    equipment_ids = _ids(payload.get("selected_equipment", []) if isinstance(payload, dict) else [], "equipment item")
    service_ids = list(dict.fromkeys(service_ids + sorted(_configured_ids(rules, "included_service_ids"))))
    equipment_ids = list(dict.fromkeys(equipment_ids + sorted(_configured_ids(rules, "included_equipment_ids"))))
    if menu_ids:
        menu_items = {
            item.id: item for item in db.query(models.MenuItem).filter(
                models.MenuItem.id.in_(menu_ids),
                models.MenuItem.caterer_id == package.caterer_id,
                models.MenuItem.is_archived.is_(False),
                models.MenuItem.is_hidden.is_(False),
                models.MenuItem.available_for_package.is_(True),
                models.MenuItem.usage_type.in_(["both", "package_only"]),
                models.MenuItem.status == "available",
            ).all()
        }
    service_records = {
        item.id: item for item in db.query(models.Service).filter(
            models.Service.id.in_(service_ids),
            models.Service.caterer_id == package.caterer_id,
            models.Service.is_archived.is_(False),
            models.Service.is_hidden.is_(False),
            models.Service.usage_type.in_(["both", "package_only"]),
            models.Service.status == "available",
        ).all()
    } if service_ids else {}
    equipment_records = {
        item.id: item for item in db.query(models.Equipment).filter(
            models.Equipment.id.in_(equipment_ids),
            models.Equipment.caterer_id == package.caterer_id,
            models.Equipment.is_archived.is_(False),
            models.Equipment.is_hidden.is_(False),
            models.Equipment.usage_type.in_(["both", "package_only"]),
            models.Equipment.status == "available",
        ).all()
    } if equipment_ids else {}
    service_addons = {
        addon.service_id: addon.price for addon in db.query(models.PackageServiceAddon).filter(
            models.PackageServiceAddon.package_id == package.id,
            models.PackageServiceAddon.service_id.in_(service_ids),
            models.PackageServiceAddon.is_enabled.is_(True),
        ).all()
    } if service_ids else {}
    equipment_addons = {
        addon.equipment_id: addon.price for addon in db.query(models.PackageEquipmentAddon).filter(
            models.PackageEquipmentAddon.package_id == package.id,
            models.PackageEquipmentAddon.equipment_id.in_(equipment_ids),
            models.PackageEquipmentAddon.is_enabled.is_(True),
        ).all()
    } if equipment_ids else {}
    return calculate_customization(
        package,
        payload,
        menu_items,
        service_records,
        equipment_records,
        service_addons,
        equipment_addons,
    )
