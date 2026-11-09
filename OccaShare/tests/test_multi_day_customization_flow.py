import os
import sys
from decimal import Decimal
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.package_pricing import calculate_customization, PackagePricingError


def test_multi_day_customization_independent_guest_counts_and_subtotals():
    pkg = SimpleNamespace(
        id=5,
        name="Elegant Wedding Package",
        caterer_id=1,
        pricing_mode="customizable",
        price_unit="per_guest",
        price_per_head=Decimal("350.00"),
        price=Decimal("350.00"),
        min_guests=50,
        max_guests=999999,
        service_duration=8,
        selection_rules={
            "available_menu_ids": [101, 102, 103, 104],
            "category_quotas": {"Beef": 1, "Chicken": 1, "Pork": 1},
        },
    )

    catalog_menu = {
        101: SimpleNamespace(id=101, name="Beef Broccoli", category="Beef", upgrade_fee=0),
        102: SimpleNamespace(id=102, name="Chicken Hong Kong", category="Chicken", upgrade_fee=Decimal("20.02")),  # upgrade fee for day 1
        103: SimpleNamespace(id=103, name="Hamonado", category="Pork", upgrade_fee=0),
        104: SimpleNamespace(id=104, name="Cordon Bleu with White Sauce", category="Chicken", upgrade_fee=0),
    }

    # Day 1: 50 pax with Chicken upgrade fee (20.02 * 50 = 1,001.00) -> Base 17,500 + 1,001 = 18,501.00
    day1_payload = {
        "event_id": "event-1",
        "guest_count": 50,
        "selected_food": [
            {"id": 101, "name": "Beef Broccoli", "category": "Beef", "upgrade_fee": 0},
            {"id": 102, "name": "Chicken Hong Kong", "category": "Chicken", "upgrade_fee": 20.02},
            {"id": 103, "name": "Hamonado", "category": "Pork", "upgrade_fee": 0},
        ],
        "selected_menu_extras": [],
        "selected_services": [],
        "selected_equipment": [],
        "removed_categories": [],
    }

    # Day 2: 400 pax, all included dishes with 0 upgrade fee -> Base 400 * 350 = 140,000.00
    day2_payload = {
        "event_id": "event-1731174620000-1",
        "guest_count": 400,
        "selected_food": [
            {"id": 101, "name": "Beef Broccoli", "category": "Beef", "upgrade_fee": 0},
            {"id": 104, "name": "Cordon Bleu with White Sauce", "category": "Chicken", "upgrade_fee": 0},
            {"id": 103, "name": "Hamonado", "category": "Pork", "upgrade_fee": 0},
        ],
        "selected_menu_extras": [],
        "selected_services": [],
        "selected_equipment": [],
        "removed_categories": [],
    }

    day1_result = calculate_customization(pkg, day1_payload, catalog_menu, {}, {})
    day2_result = calculate_customization(pkg, day2_payload, catalog_menu, {}, {})

    # Day 1 checks
    assert day1_result["guest_count"] == 50
    assert day1_result["base_price"] == Decimal("350.00")
    assert day1_result["estimated_total"] == Decimal("18501.00")

    # Day 2 checks
    assert day2_result["guest_count"] == 400
    assert day2_result["base_price"] == Decimal("350.00")
    assert day2_result["estimated_total"] == Decimal("140000.00")

    # Independent data flow checks
    assert day1_result["guest_count"] != day2_result["guest_count"]
    total_guests = day1_result["guest_count"] + day2_result["guest_count"]
    assert total_guests == 450

    total_booking_estimate = day1_result["estimated_total"] + day2_result["estimated_total"]
    assert total_booking_estimate == Decimal("158501.00")
