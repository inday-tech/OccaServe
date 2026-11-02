from types import SimpleNamespace

import pytest

from app.services.quotation import quotation_service


class QuotationQuery:
    def filter(self, *_args):
        return self

    def first(self):
        return None


class QuotationDatabase:
    def __init__(self):
        self.added = []

    def query(self, _model):
        return QuotationQuery()

    def add(self, item):
        self.added.append(item)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, _item):
        pass


def make_booking(transportation_status):
    return SimpleNamespace(
        id=1,
        guest_count=10,
        status="pending_review",
        travel_fee=300,
        travel_fee_status=transportation_status,
        document_type="booking_agreement",
        reservation_fee=0,
        total_amount=0,
        total_price=0,
        caterer=SimpleNamespace(
            accepted_payment_terms=[30],
            rental_policies=None,
            general_terms="",
            terms_and_conditions="",
        ),
        package=SimpleNamespace(
            name="Custom Package",
            pricing_mode="customizable",
            price_per_head=100,
            price=100,
            description="",
            inclusions=[],
        ),
        custom_requirements={
            "customization": {
                "base_price": 100,
                "selected_food": [{
                    "id": 8,
                    "name": "Chicken",
                    "price": 0,
                    "upgrade_fee": 0,
                    "unit": "pax",
                    "qty": 10,
                }],
                "selected_menu_extras": [],
                "selected_services": [],
                "selected_equipment": [],
                "food_removal_credit": 0,
            },
        },
    )


@pytest.mark.parametrize(
    ("transportation_status", "expected_fee"),
    [("calculated", 300), ("manual_quote", 0), ("waived", 0)],
)
def test_customizable_quotation_includes_only_confirmed_transport_fees(
    transportation_status, expected_fee
):
    booking = make_booking(transportation_status)

    quotation = quotation_service._create_customizable_quotation(
        QuotationDatabase(), booking, 30
    )

    assert quotation.package_details["transportation_total"] == expected_fee
    assert quotation.package_details["transportation_status"] == transportation_status
    assert quotation.total_amount == 1000 + expected_fee
