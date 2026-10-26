from types import SimpleNamespace

from app.services.capacity_service import _booked_service_capacity


def test_staff_service_capacity_uses_guest_count_not_charge_quantity():
    service = SimpleNamespace(
        capacity_type="staff_based",
        staff_to_pax_ratio=25,
        min_staff_required=2,
        unit_type="per_guest",
    )
    booking = SimpleNamespace(guest_count=42)
    item = SimpleNamespace(quantity=42)

    assert _booked_service_capacity(service, booking, item) == 2


def test_per_guest_service_uses_one_inventory_unit():
    service = SimpleNamespace(capacity_type="unit_based", unit_type="per_guest")
    booking = SimpleNamespace(guest_count=42)
    item = SimpleNamespace(quantity=42)

    assert _booked_service_capacity(service, booking, item) == 1


def test_per_event_service_uses_saved_quantity():
    service = SimpleNamespace(capacity_type="unit_based", unit_type="per_event")
    booking = SimpleNamespace(guest_count=42)
    item = SimpleNamespace(quantity=3)

    assert _booked_service_capacity(service, booking, item) == 3
