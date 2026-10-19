from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.bookings import _cart_item_types
from app.routers.customer_dashboard import _is_legacy_food_order


@pytest.mark.parametrize(
    ("cart_data", "expected"),
    [
        ('[{"type":"Menu"}]', (True, False, False)),
        ('[{"type":"Equipment"}]', (False, True, False)),
        ('[{"type":"Service"}]', (False, False, True)),
        ('[{"type":"Equipment"},{"type":"Service"}]', (False, True, True)),
        ('[{"type":"Menu"},{"type":"Equipment"}]', (True, True, False)),
    ],
)
def test_cart_item_types_classifies_supported_items(cart_data, expected):
    assert _cart_item_types(cart_data) == expected


@pytest.mark.parametrize(
    "cart_data",
    [
        "not-json",
        "{}",
        "[null]",
        '[{"type":[]}]',
        '[{"type":"Unknown"}]',
    ],
)
def test_cart_item_types_rejects_invalid_items(cart_data):
    with pytest.raises(HTTPException) as exc_info:
        _cart_item_types(cart_data)

    assert exc_info.value.status_code == 400


def make_booking(
    document_type,
    event_type,
    event_name="",
    selected_items=None,
    transaction_type="fast_track",
):
    return SimpleNamespace(
        document_type=document_type,
        event_type=event_type,
        event_name=event_name,
        selected_items=selected_items or [],
        transaction_type=transaction_type,
    )


def make_item(menu_item_id=None, equipment_id=None, service_id=None):
    return SimpleNamespace(
        menu_item_id=menu_item_id,
        equipment_id=equipment_id,
        service_id=service_id,
    )


def test_legacy_food_orders_are_hidden_but_service_invoices_are_kept():
    food_invoice = make_booking(
        "invoice",
        "Ala Carte Order",
        "Food Order: Customer",
        [make_item(menu_item_id=1)],
    )
    service_invoice = make_booking(
        "invoice",
        "Service Booking",
        "Service Request: Sound system",
        [make_item(service_id=1)],
    )

    assert _is_legacy_food_order(food_invoice)
    assert not _is_legacy_food_order(service_invoice)
