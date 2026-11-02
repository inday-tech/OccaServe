from decimal import Decimal

from app.db import models
from app.routers.caterer_dashboard import calculate_fixed_package_total


def test_fixed_package_total_uses_package_extra_guest_rate():
    assert calculate_fixed_package_total(Decimal("125.50"), 40) == Decimal("5020.00")


def test_fixed_package_total_rejects_missing_rate_or_guest_count():
    assert calculate_fixed_package_total(0, 40) is None
    assert calculate_fixed_package_total(125, 0) is None


def test_package_booking_count_includes_only_its_real_non_draft_bookings():
    package = models.CateringPackage(id=17)
    package.bookings = [
        models.Booking(package_id=17, status="confirmed", is_archived=False),
        models.Booking(package_id=17, status="pending", is_archived=False),
        models.Booking(package_id=17, status="draft", is_archived=False),
        models.Booking(package_id=17, status="confirmed", is_archived=True),
        models.Booking(package_id=18, status="confirmed", is_archived=False),
    ]

    assert package.total_bookings_count == 2


def test_package_without_bookings_has_zero_booking_count():
    package = models.CateringPackage(id=17)

    assert package.total_bookings_count == 0
