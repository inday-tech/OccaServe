from types import SimpleNamespace
import pytest
from app.services.preparation_service import normalize_prep_status, PREP_STATUSES


def test_allowed_dispatch_from_stages():
    # Test food order allowed dispatch
    food_order = SimpleNamespace(
        document_type="invoice",
        status="confirmed",
        preparation_status="not_started",
    )
    is_food_order = (food_order.document_type == "invoice")
    allowed_dispatch_from = {
        "ready_for_delivery": {"preparing", "confirmed"},
        "ready_for_pickup": {"preparing", "confirmed"},
        "on_the_way": {"ready_for_delivery", "ready_for_pickup", "preparing", "confirmed"},
    }
    assert food_order.status in allowed_dispatch_from["ready_for_delivery"]
    assert is_food_order is True


def test_catering_booking_prep_status_sync():
    # Test catering booking with preparing status
    booking = SimpleNamespace(
        document_type="booking",
        status="confirmed",
        preparation_status="preparing",
    )
    is_food_order = (booking.document_type == "invoice")
    assert is_food_order is False

    current_prep = normalize_prep_status(booking.preparation_status, booking.status)
    assert current_prep == "preparing"

    prep_order = [s["key"] for s in PREP_STATUSES]
    # Should not block since it is at least 'preparing'
    assert not (prep_order.index(current_prep) < prep_order.index("preparing"))


def test_catering_booking_not_started_blocked():
    # Test catering booking when preparation has not started
    booking = SimpleNamespace(
        document_type="booking",
        status="confirmed",
        preparation_status="not_started",
    )
    is_food_order = (booking.document_type == "invoice")
    current_prep = normalize_prep_status(booking.preparation_status, booking.status)
    prep_order = [s["key"] for s in PREP_STATUSES]

    # Should be blocked because index < 'preparing'
    is_blocked = not is_food_order and prep_order.index(current_prep) < prep_order.index("preparing")
    assert is_blocked is True
