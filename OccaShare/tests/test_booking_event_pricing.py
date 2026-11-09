import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import models
from app.services.booking_event_pricing import calculate_event_estimate


def test_event_estimate_uses_catalog_prices_and_does_not_double_charge_inclusions():
    package = models.CateringPackage(
        pricing_mode="per_pax",
        price_unit="per_guest",
        price_per_head=350,
        min_guests=10,
    )
    package.menu_items = [
        models.MenuItem(id=1, name="Included dish", price=999, pricing_unit="per_pax", is_addon=False)
    ]
    package.equipment_links = [models.PackageEquipment(equipment_id=10)]
    package.service_links = [models.PackageService(service_id=20)]
    package.menu_addons = [models.PackageMenuAddon(menu_item_id=3, price=30, is_enabled=True)]
    package.equipment_addons = [models.PackageEquipmentAddon(equipment_id=11, price=40, is_enabled=True)]
    package.service_addons = [models.PackageServiceAddon(service_id=21, price=500, is_enabled=True)]

    estimate = calculate_event_estimate(
        {"guest_count": 50},
        package,
        [
            models.MenuItem(id=1, price=999, pricing_unit="per_pax", is_addon=False),
            models.MenuItem(id=2, price=100, pricing_unit="per_guest", is_addon=False),
            models.MenuItem(id=3, price=45, addon_price=45, pricing_unit="per_pax", is_addon=True),
        ],
        [
            models.Equipment(id=10, rental_price=90, addon_price=90),
            models.Equipment(id=11, rental_price=70, addon_price=70),
        ],
        [
            models.Service(id=20, selling_price=600, addon_price=600, unit_type="per_event"),
            models.Service(id=21, selling_price=700, addon_price=700, unit_type="per_event"),
        ],
    )

    assert estimate == {
        "package": 17500.0,
        "menu": 6500.0,
        "equipment": 40.0,
        "services": 500.0,
        "subtotal": 24540.0,
    }


def test_fixed_event_estimate_uses_package_price_and_configured_excess_guest_fee():
    package = models.CateringPackage(
        pricing_mode="fixed",
        price_unit="fixed",
        price=10000,
        min_guests=50,
        additional_guest_price=200,
    )

    estimate = calculate_event_estimate(
        {"guest_count": 60},
        package,
        [],
        [],
        [],
    )

    assert estimate["package"] == 12000.0
    assert estimate["subtotal"] == 12000.0
