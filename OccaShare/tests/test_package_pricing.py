from types import SimpleNamespace

import pytest

from app.services.package_pricing import (
    PackagePricingError,
    calculate_customization,
    validate_customizable_addon_rules,
    validate_customizable_menu_extra_options,
    validate_customizable_menu_rules,
)


def package(**overrides):
    values = {
        "id": 10,
        "caterer_id": 5,
        "name": "Custom Celebration",
        "pricing_mode": "customizable",
        "price_per_head": 100.0,
        "price": 100.0,
        "min_guests": 10,
        "max_guests": 100,
        "service_duration": 4,
        "selection_rules": {
            "available_menu_ids": [1, 2, 6],
            "available_service_ids": [3, 4],
            "available_equipment_ids": [5],
            "category_quotas": {"Main": 2},
            "category_removal_credits": {"Dessert": 20},
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def catalog():
    return (
        {
            1: SimpleNamespace(id=1, name="Chicken", category="Main", upgrade_fee=25),
            2: SimpleNamespace(id=2, name="Fish", category="Main", upgrade_fee=0),
            6: SimpleNamespace(id=6, name="Cake", category="Dessert", upgrade_fee=0),
        },
        {
            3: SimpleNamespace(
                id=3, name="Waitstaff", category="Staff", unit_type="per_guest",
                selling_price=10, capacity_type="staff_based", staff_to_pax_ratio=25,
                min_staff_required=2, minimum_hours=1,
            ),
            4: SimpleNamespace(
                id=4, name="Setup", category="Setup", unit_type="per_event",
                selling_price=500, capacity_type="unit_based", minimum_hours=1,
            ),
        },
        {
            5: SimpleNamespace(
                id=5, name="Tables", unit_type="set", addon_price=0,
                rental_price=1000, available_qty=4,
            ),
        },
    )


def test_recalculates_client_supplied_prices_from_catalog():
    menu, services, equipment = catalog()
    result = calculate_customization(
        package(),
        {
            "guest_count": 40,
            "selected_food": [{"id": 1, "price": 0, "qty": 1}],
            "selected_services": [{"id": 3, "price": 1, "qty": 1}],
            "selected_equipment": [{"id": 5, "price": 1, "qty": 1}],
            "estimated_total": 1,
            "base_price": 1,
        },
        menu,
        services,
        equipment,
    )

    assert result["base_package_total"] == 4000
    assert result["food_total"] == 1000
    assert result["services_total"] == 400
    assert result["selected_services"][0]["qty"] == 40
    assert result["selected_services"][0]["capacity_qty"] == 2
    assert result["equipment_total"] == 1000
    assert result["estimated_total"] == 6400
    assert result["selected_equipment"][0]["qty"] == 1


def test_fixed_service_charge_is_applied_once():
    menu, services, equipment = catalog()
    result = calculate_customization(
        package(),
        {"guest_count": 20, "selected_food": [], "selected_services": [4], "selected_equipment": []},
        menu,
        services,
        equipment,
    )

    assert result["services_total"] == 500


def test_package_service_price_override_and_included_service_are_authoritative():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "service_prices": {"3": 15},
        "included_service_ids": [4],
    })
    result = calculate_customization(
        pkg,
        {"guest_count": 20, "selected_food": [], "selected_services": [3], "selected_equipment": []},
        menu,
        services,
        equipment,
    )

    assert result["services_total"] == 300
    assert result["selected_services"][0]["price"] == 15
    assert result["selected_services"][1]["included"] is True
    assert result["selected_services"][1]["subtotal"] == 0


def test_service_priced_per_staff_member_uses_required_staff_count():
    menu, services, equipment = catalog()
    services[7] = SimpleNamespace(
        id=7, name="Servers", category="Staff", unit_type="per_staff_member",
        selling_price=300, capacity_type="unit_based", staff_to_pax_ratio=25,
        min_staff_required=1,
    )
    pkg = package(selection_rules={
        **package().selection_rules,
        "available_service_ids": [3, 4, 7],
    })
    result = calculate_customization(
        pkg,
        {"guest_count": 40, "selected_food": [], "selected_services": [7], "selected_equipment": []},
        menu,
        services,
        equipment,
    )

    assert result["services_total"] == 600
    assert result["selected_services"][0]["qty"] == 2


def test_included_addons_are_added_even_if_client_omits_them():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "included_service_ids": [4],
        "included_equipment_ids": [5],
    })
    result = calculate_customization(
        pkg,
        {"guest_count": 20, "selected_food": [], "selected_services": [], "selected_equipment": []},
        menu,
        services,
        equipment,
    )

    assert result["services_total"] == 0
    assert result["equipment_total"] == 0
    assert result["selected_services"][0]["included"] is True
    assert result["selected_equipment"][0]["included"] is True


def test_equipment_uses_package_price_and_enforces_quantity_limit():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "equipment_prices": {"5": 250},
        "equipment_quantity_limits": {"5": 3},
    })
    result = calculate_customization(
        pkg,
        {
            "guest_count": 20,
            "selected_food": [],
            "selected_services": [],
            "selected_equipment": [{"id": 5, "qty": 2, "price": 0}],
        },
        menu,
        services,
        equipment,
    )

    assert result["equipment_total"] == 500
    assert result["selected_equipment"][0]["qty"] == 2
    assert result["selected_equipment"][0]["price"] == 250

    with pytest.raises(PackagePricingError, match="currently unavailable"):
        calculate_customization(
            pkg,
            {
                "guest_count": 20,
                "selected_food": [],
                "selected_services": [],
                "selected_equipment": [{"id": 5, "qty": 4}],
            },
            menu,
            services,
            equipment,
        )


def test_addon_rules_reject_unselected_items_and_invalid_prices():
    with pytest.raises(PackagePricingError, match="belong to available"):
        validate_customizable_addon_rules({
            "available_service_ids": [3],
            "service_prices": {"4": 100},
        })
    with pytest.raises(PackagePricingError, match="valid and belong"):
        validate_customizable_addon_rules({
            "available_equipment_ids": [5],
            "equipment_prices": {"5": 0},
        })
    with pytest.raises(PackagePricingError, match="Included services and equipment"):
        validate_customizable_addon_rules({
            "available_service_ids": [3],
            "included_service_ids": [4],
        })


def test_extra_dish_uses_package_price_and_quantity_once():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "menu_extra_options": {"1": {"price": 80, "max_quantity": 3}},
    })
    result = calculate_customization(
        pkg,
        {
            "guest_count": 20,
            "selected_food": [],
            "selected_menu_extras": [{"id": 1, "qty": 2, "price": 1}],
            "selected_services": [],
            "selected_equipment": [],
        },
        menu,
        services,
        equipment,
    )

    assert result["menu_extras_total"] == 160
    assert result["selected_menu_extras"] == [{
        "id": 1,
        "name": "Chicken",
        "category": "Main",
        "price": 80,
        "size": "Standard serving",
        "unit": "tray",
        "qty": 2,
        "subtotal": 160,
    }]
    assert result["estimated_total"] == 2160


def test_package_extra_dish_rules_require_selected_menu_items_and_valid_prices():
    rules = {
        "available_menu_ids": [1],
        "menu_extra_options": {
            "1": {
                "variants": [
                    {"size": "Half tray", "price": 80},
                    {"size": "Full tray", "price": 150},
                ],
                "max_quantity": 2,
            }
        },
    }
    validated = validate_customizable_menu_extra_options(rules)
    assert validated[1]["variants"] == [
        {"size": "Half tray", "price": 80},
        {"size": "Full tray", "price": 150},
    ]
    assert validated[1]["max_quantity"] == 2

    with pytest.raises(PackagePricingError, match="available menu"):
        validate_customizable_menu_extra_options({
            "available_menu_ids": [2],
            "menu_extra_options": {"1": {"price": 80, "max_quantity": 2}},
        })
    with pytest.raises(PackagePricingError, match="greater than"):
        validate_customizable_menu_extra_options({
            "available_menu_ids": [1],
            "menu_extra_options": {"1": {"price": 0, "max_quantity": 2}},
        })
    with pytest.raises(PackagePricingError, match="unique name"):
        validate_customizable_menu_extra_options({
            "available_menu_ids": [1],
            "menu_extra_options": {
                "1": {
                    "variants": [
                        {"size": "Full tray", "price": 100},
                        {"size": "full tray", "price": 120},
                    ]
                }
            },
        })


def test_extra_dish_size_uses_caterer_price_not_customer_payload_price():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "menu_extra_options": {
            "1": {
                "variants": [
                    {"size": "Half tray (serves 10)", "price": 500},
                    {"size": "Full tray (serves 20)", "price": 900},
                ]
            }
        },
    })

    result = calculate_customization(
        pkg,
        {
            "guest_count": 20,
            "selected_food": [],
            "selected_menu_extras": [{
                "id": 1,
                "size": "Full tray (serves 20)",
                "qty": 2,
                "price": 1,
            }],
            "selected_services": [],
            "selected_equipment": [],
        },
        menu,
        services,
        equipment,
    )

    assert result["menu_extras_total"] == 1800
    assert result["selected_menu_extras"][0]["price"] == 900
    assert result["selected_menu_extras"][0]["size"] == "Full tray (serves 20)"
    assert result["selected_menu_extras"][0]["subtotal"] == 1800

    with pytest.raises(PackagePricingError, match="available size"):
        calculate_customization(
            pkg,
            {
                "guest_count": 20,
                "selected_food": [],
                "selected_menu_extras": [{"id": 1, "size": "XXL tray", "qty": 1}],
                "selected_services": [],
                "selected_equipment": [],
            },
            menu,
            services,
            equipment,
        )


def test_package_extra_dish_quantity_defaults_to_unrestricted_customer_ordering():
    validated = validate_customizable_menu_extra_options({
        "available_menu_ids": [1],
        "menu_extra_options": {"1": {"price": 80}},
    })

    assert validated[1]["max_quantity"] == 999


def test_included_menu_slot_and_explicit_replacement_fee_are_enforced():
    menu, services, equipment = catalog()
    menu[1].category = "Main"
    menu[2].category = "Main"
    rules = {
        "available_menu_ids": [1, 2],
        "included_menu_ids": [1],
        "category_quotas": {"Main": 1},
        "menu_replacements": {"1": {"2": 35}},
    }
    validate_customizable_menu_rules(rules, menu)
    pkg = package(selection_rules=rules)

    included = calculate_customization(
        pkg,
        {"guest_count": 20, "selected_food": [1], "selected_services": [], "selected_equipment": []},
        menu,
        services,
        equipment,
    )
    assert included["food_total"] == 0
    assert included["selected_food"][0]["replacement_for"] is None

    replacement = calculate_customization(
        pkg,
        {"guest_count": 20, "selected_food": [2], "selected_services": [], "selected_equipment": []},
        menu,
        services,
        equipment,
    )
    assert replacement["food_total"] == 700
    assert replacement["selected_food"][0]["replacement_for"] == 1
    assert replacement["selected_food"][0]["replacement_for_name"] == "Chicken"


def test_menu_slot_can_swap_across_categories_with_explicit_per_guest_fee():
    menu, services, equipment = catalog()
    menu[1].category = "Chicken"
    menu[7] = SimpleNamespace(id=7, name="Beef", category="Beef", upgrade_fee=0)
    rules = {
        "available_menu_ids": [1, 7],
        "included_menu_ids": [1],
        "category_quotas": {"Chicken": 1},
        "menu_replacements": {"1": {"7": 45}},
    }
    validate_customizable_menu_rules(rules, menu)
    result = calculate_customization(
        package(selection_rules=rules),
        {
            "guest_count": 20,
            "selected_food": [7],
            "selected_services": [],
            "selected_equipment": [],
        },
        menu,
        services,
        equipment,
    )

    assert result["food_total"] == 900
    assert result["selected_food"][0]["category"] == "Beef"
    assert result["selected_food"][0]["replacement_for"] == 1
    assert result["selected_food"][0]["replacement_for_name"] == "Chicken"


def test_cross_category_replacements_assign_to_their_approved_slots_once():
    menu, services, equipment = catalog()
    menu[1].category = "Chicken"
    menu[6].category = "Dessert"
    menu[7] = SimpleNamespace(id=7, name="Beef", category="Beef", upgrade_fee=0)
    menu[8] = SimpleNamespace(id=8, name="Fruit Tart", category="Dessert", upgrade_fee=0)
    rules = {
        "available_menu_ids": [1, 6, 7, 8],
        "included_menu_ids": [1, 6],
        "category_quotas": {"Chicken": 1, "Dessert": 1},
        "menu_replacements": {"1": {"7": 45}, "6": {"8": 25}},
    }
    result = calculate_customization(
        package(selection_rules=rules),
        {
            "guest_count": 10,
            "selected_food": [7, 8],
            "selected_services": [],
            "selected_equipment": [],
        },
        menu,
        services,
        equipment,
    )

    assert result["food_total"] == 700
    assert [(item["id"], item["replacement_for"], item["upgrade_fee"]) for item in result["selected_food"]] == [
        (7, 1, 45),
        (8, 6, 25),
    ]


def test_explicit_zero_fee_allows_a_free_cross_category_replacement():
    menu, services, equipment = catalog()
    menu[1].category = "Chicken"
    menu[7] = SimpleNamespace(id=7, name="Vegetable Curry", category="Vegetarian", upgrade_fee=0)
    rules = {
        "available_menu_ids": [1, 7],
        "included_menu_ids": [1],
        "category_quotas": {"Chicken": 1},
        "menu_replacements": {"1": {"7": 0}},
    }
    validate_customizable_menu_rules(rules, menu)
    result = calculate_customization(
        package(selection_rules=rules),
        {
            "guest_count": 20,
            "selected_food": [7],
            "selected_services": [],
            "selected_equipment": [],
        },
        menu,
        services,
        equipment,
    )

    assert result["food_total"] == 0
    assert result["selected_food"][0]["replacement_for"] == 1
    assert result["selected_food"][0]["upgrade_fee"] == 0


def test_cross_category_replacement_is_not_valid_after_its_slot_category_is_removed():
    menu, services, equipment = catalog()
    menu[1].category = "Chicken"
    menu[7] = SimpleNamespace(id=7, name="Beef", category="Beef", upgrade_fee=0)
    pkg = package(selection_rules={
        "available_menu_ids": [1, 7],
        "included_menu_ids": [1],
        "category_quotas": {"Chicken": 1},
        "menu_replacements": {"1": {"7": 45}},
    })

    with pytest.raises(PackagePricingError, match="not an approved replacement"):
        calculate_customization(
            pkg,
            {
                "guest_count": 10,
                "selected_food": [7],
                "selected_services": [],
                "selected_equipment": [],
                "removed_categories": ["Chicken"],
            },
            menu,
            services,
            equipment,
        )


def test_customizable_menu_requires_an_included_slot_when_options_are_available():
    menu, _, _ = catalog()

    with pytest.raises(PackagePricingError, match="at least one included default dish"):
        validate_customizable_menu_rules({
            "available_menu_ids": [1, 2],
            "included_menu_ids": [],
            "menu_replacements": {},
        }, menu)


def test_included_menu_rules_reject_unapproved_or_missing_replacement():
    menu, services, equipment = catalog()
    menu[1].category = "Main"
    menu[2].category = "Main"
    pkg = package(selection_rules={
        "available_menu_ids": [1, 2],
        "included_menu_ids": [1],
        "category_quotas": {"Main": 1},
        "menu_replacements": {},
    })
    with pytest.raises(PackagePricingError, match="not an approved replacement"):
        calculate_customization(
            pkg,
            {"guest_count": 20, "selected_food": [2], "selected_services": [], "selected_equipment": []},
            menu,
            services,
            equipment,
        )
    with pytest.raises(PackagePricingError, match="Choose the included"):
        calculate_customization(
            pkg,
            {"guest_count": 20, "selected_food": [], "selected_services": [], "selected_equipment": []},
            menu,
            services,
            equipment,
        )


def test_extra_dish_requires_explicit_configuration_and_quantity_limit():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "menu_extra_options": {"1": {"price": 80, "max_quantity": 2}},
    })
    payload = {
        "guest_count": 20,
        "selected_food": [],
        "selected_menu_extras": [{"id": 1, "qty": 3}],
        "selected_services": [],
        "selected_equipment": [],
    }

    with pytest.raises(PackagePricingError, match="quantity must be between 1 and 2"):
        calculate_customization(pkg, payload, menu, services, equipment)

    with pytest.raises(PackagePricingError, match="no longer available"):
        calculate_customization(
            package(),
            {**payload, "selected_menu_extras": [{"id": 1, "qty": 1}]},
            menu,
            services,
            equipment,
        )


def test_extra_dish_cannot_bypass_removed_category_credit_rules():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "menu_extra_options": {"6": {"price": 120, "max_quantity": 2}},
    })
    with pytest.raises(PackagePricingError, match="Remove the selected Dessert item"):
        calculate_customization(
            pkg,
            {
                "guest_count": 20,
                "selected_food": [],
                "selected_menu_extras": [{"id": 6, "qty": 1}],
                "selected_services": [],
                "selected_equipment": [],
                "removed_categories": ["Dessert"],
            },
            menu,
            services,
            equipment,
        )


def test_included_menu_dish_can_also_be_ordered_as_an_extra():
    menu, services, equipment = catalog()
    pkg = package(selection_rules={
        **package().selection_rules,
        "included_menu_ids": [1, 2],
        "menu_extra_options": {"1": {"price": 80, "max_quantity": 2}},
    })
    result = calculate_customization(
        pkg,
        {
            "guest_count": 20,
            "selected_food": [1, 2],
            "selected_menu_extras": [{"id": 1, "size": "Standard serving", "qty": 1}],
            "selected_services": [],
            "selected_equipment": [],
        },
        menu,
        services,
        equipment,
    )

    assert result["food_total"] == 0
    assert result["menu_extras_total"] == 80
    assert result["selected_food"][0]["id"] == 1
    assert result["selected_menu_extras"][0]["id"] == 1
    assert result["estimated_total"] == 2080


def test_rejects_guest_count_outside_package_limits():
    menu, services, equipment = catalog()
    with pytest.raises(PackagePricingError, match="at most 100"):
        calculate_customization(
            package(),
            {"guest_count": 101, "selected_food": [], "selected_services": [], "selected_equipment": []},
            menu,
            services,
            equipment,
        )


def test_rejects_items_not_allowed_by_package():
    menu, services, equipment = catalog()
    with pytest.raises(PackagePricingError, match="no longer available"):
        calculate_customization(
            package(),
            {"guest_count": 20, "selected_food": [99], "selected_services": [], "selected_equipment": []},
            menu,
            services,
            equipment,
        )


def test_enforces_only_explicit_category_quotas():
    menu, services, equipment = catalog()
    with pytest.raises(PackagePricingError, match="no more than 1"):
        calculate_customization(
            package(selection_rules={**package().selection_rules, "category_quotas": {"Main": 1}}),
            {"guest_count": 20, "selected_food": [1, 2], "selected_services": [], "selected_equipment": []},
            menu,
            services,
            equipment,
        )


def test_removal_credit_requires_explicit_configuration_and_empty_category():
    menu, services, equipment = catalog()
    result = calculate_customization(
        package(),
        {"guest_count": 20, "selected_food": [], "selected_services": [], "selected_equipment": [], "removed_categories": ["Dessert"]},
        menu,
        services,
        equipment,
    )
    assert result["food_removal_credit"] == 400
    assert result["estimated_total"] == 1600

    with pytest.raises(PackagePricingError, match="Remove the selected"):
        calculate_customization(
            package(),
            {"guest_count": 20, "selected_food": [1], "selected_services": [], "selected_equipment": [], "removed_categories": ["Main"]},
            menu,
            services,
            equipment,
        )


def test_requires_caterer_review_for_unpriced_optional_services():
    menu, services, equipment = catalog()
    services[3].selling_price = 0
    with pytest.raises(PackagePricingError, match="Ask the caterer to review"):
        calculate_customization(
            package(),
            {"guest_count": 20, "selected_food": [], "selected_services": [3], "selected_equipment": []},
            menu,
            services,
            equipment,
        )


def test_rejects_invalid_monetary_values():
    menu, services, equipment = catalog()
    menu[1].upgrade_fee = -1
    with pytest.raises(PackagePricingError, match="cannot be negative"):
        calculate_customization(
            package(),
            {"guest_count": 20, "selected_food": [1], "selected_services": [], "selected_equipment": []},
            menu,
            services,
            equipment,
        )
