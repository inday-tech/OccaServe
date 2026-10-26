import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.db import models
from app.routers import caterer_dashboard
from app.routers import quotations
from app.services.quotation import quotation_service, revise_quotation


class QuotationQuery:
    def __init__(self, quotation):
        self.quotation = quotation

    def options(self, *_args):
        return self

    def filter(self, *_args):
        return self

    def first(self):
        return self.quotation


class QuotationDatabase:
    def __init__(self, quotation):
        self.quotation = quotation

    def query(self, model):
        assert model is models.Quotation
        return QuotationQuery(self.quotation)


def test_customer_cannot_sign_before_caterer(monkeypatch):
    customer = SimpleNamespace(id=12)
    booking = SimpleNamespace(
        id=34,
        user_id=customer.id,
        caterer=SimpleNamespace(user_id=56),
    )
    quotation = SimpleNamespace(
        booking=booking,
        caterer_signature=None,
        customer_signature=None,
    )
    db = QuotationDatabase(quotation)
    monkeypatch.setattr(quotations, "get_session_user", lambda _request, _db: customer)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            quotations.sign_contract(
                booking_id=booking.id,
                request=object(),
                background_tasks=BackgroundTasks(),
                data={
                    "signature_data": "data:image/png;base64,signature",
                    "confirm_agreement": True,
                },
                db=db,
            )
        )

    assert error.value.status_code == 409
    assert "caterer must sign" in error.value.detail.lower()


class QuotationWriteDatabase:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)

    def flush(self):
        pass

    def commit(self):
        pass

    def refresh(self, _item):
        pass


class BookingQuery:
    def __init__(self, booking):
        self.booking = booking

    def get(self, _booking_id):
        return self.booking


class BookingWriteDatabase(QuotationWriteDatabase):
    def __init__(self, booking):
        super().__init__()
        self.booking = booking
        self.deleted = []

    def query(self, model):
        assert model is models.Booking
        return BookingQuery(self.booking)

    def delete(self, item):
        self.deleted.append(item)


def test_caterer_cannot_revise_after_payment_request_activation():
    profile = SimpleNamespace(id=9)
    booking = SimpleNamespace(
        id=42,
        caterer_id=profile.id,
        status="pending_quotation",
        payment_request_activated_at="activated",
        payment_deadline_at=None,
        quotation=SimpleNamespace(
            status="quoted",
            caterer_signature=None,
            customer_signature=None,
        ),
    )
    db = BookingWriteDatabase(booking)
    user = SimpleNamespace(id=7, caterer_profile=profile)

    with pytest.raises(HTTPException) as error:
        asyncio.run(caterer_dashboard.submit_proposal_maker(
            booking_id=str(booking.id),
            request=SimpleNamespace(query_params={"revision": "true"}),
            base_price=Decimal("3000"),
            addon_names=[],
            addon_prices=[],
            revision_reason="Venue requirements changed",
            revision_item_changes="Replace the soup with vegetable soup",
            db=db,
            user=user,
        ))

    assert error.value.status_code == 409
    assert booking.quotation.status == "quoted"
    assert db.added == []


def test_sending_revision_requires_customer_to_review_and_notifies(monkeypatch):
    profile = SimpleNamespace(
        id=9,
        business_name="Sample Caterer",
        accepted_payment_terms=[30, 50],
    )
    quotation = SimpleNamespace(
        status="draft",
        package_details={
            "revision_number": 2,
            "revision_pending": True,
            "accepted_payment_terms": [30, 50],
            "agreement_terms": "Current terms",
        },
        total_amount=5000,
        downpayment_percent=30,
    )
    booking = SimpleNamespace(
        id=42,
        caterer_id=profile.id,
        user_id=12,
        status="pending_quotation",
        quotation=quotation,
        payment_request_activated_at=None,
        payment_deadline_at=None,
        expires_at="old-expiration",
        reservation_fee=0,
        total_amount=0,
        total_price=0,
        is_custom_event=False,
        travel_fee_status=None,
        package=None,
    )
    db = BookingWriteDatabase(booking)
    user = SimpleNamespace(id=7, caterer_profile=profile)
    notifications = []

    async def notify_status_update(*args):
        notifications.append(args)

    monkeypatch.setattr(
        caterer_dashboard.NotificationService,
        "notify_status_update",
        notify_status_update,
    )

    response = asyncio.run(caterer_dashboard.send_standard_quotation(
        booking_id=str(booking.id),
        request=SimpleNamespace(query_params={}),
        db=db,
        user=user,
    ))

    assert response.status_code == 303
    assert response.headers["location"] == f"/caterer/bookings/{booking.id}/quotation"
    assert quotation.status == "quoted"
    assert quotation.package_details["revision_pending"] is False
    assert booking.status == "pending_quotation"
    assert booking.expires_at is None
    assert booking.reservation_fee == 1500
    assert len(notifications) == 1
    assert notifications[0][1] == booking.user_id
    assert "Revised quotation ready" in notifications[0][2]
    assert any(isinstance(item, models.BookingHistory) for item in db.added)


def test_revising_quote_archives_snapshot_and_resets_approval_signatures():
    db = QuotationWriteDatabase()
    quotation = SimpleNamespace(
        id=17,
        booking=SimpleNamespace(guest_count=20),
        package_details={"revision_number": 1, "base_amount": 2000, "revision_pending": False},
        addons=[{"name": "Delivery", "price": 300}],
        total_amount=2300,
        downpayment_percent=30,
        status="awaiting_customer",
        caterer_signature="caterer-signature",
        customer_signature=None,
        caterer_signed_at="signed-at",
        customer_signed_at=None,
        customer_approved_at="approved-at",
        contract_url="/signed-contract.pdf",
    )

    new_version = revise_quotation(
        db,
        quotation,
        created_by_user_id=5,
        revision_reason="Venue access changed",
        base_amount=2100,
        addons=[{"name": "Additional setup", "price": 400}],
        total_amount=2500,
        revision_item_changes="Replace the fish dish with grilled chicken",
    )

    archived = db.added[0]
    assert new_version == 2
    assert archived.revision_number == 1
    assert archived.total_amount == 2300
    assert archived.addons == [{"name": "Delivery", "price": 300}]
    assert archived.caterer_signature == "caterer-signature"
    assert archived.customer_approved_at == "approved-at"
    assert quotation.package_details["revision_number"] == 2
    assert quotation.package_details["revision_note"] == "Venue access changed"
    assert quotation.package_details["revision_item_changes"] == "Replace the fish dish with grilled chicken"
    assert quotation.package_details["revision_pending"] is True
    assert quotation.total_amount == 2500
    assert quotation.status == "draft"
    assert quotation.caterer_signature is None
    assert quotation.customer_signature is None
    assert quotation.caterer_signed_at is None
    assert quotation.customer_approved_at is None
    assert quotation.contract_url is None


def test_customizable_quotation_preserves_and_charges_package_extra_dishes():
    booking = SimpleNamespace(
        id=42,
        guest_count=10,
        status="draft",
        travel_fee=0,
        document_type=None,
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
                    "name": "Fish",
                    "category": "Main",
                    "price": 25,
                    "upgrade_fee": 25,
                    "unit": "pax",
                    "qty": 10,
                    "subtotal": 250,
                    "replacement_for": 7,
                    "replacement_for_name": "Chicken",
                }],
                "selected_menu_extras": [{
                    "id": 7,
                    "name": "Extra Chicken",
                    "category": "Main",
                    "price": 80,
                    "unit": "dish",
                    "qty": 2,
                    "subtotal": 160,
                }],
                "selected_services": [{
                    "id": 2, "name": "Setup", "price": 0, "qty": 1,
                    "unit": "per_event", "subtotal": 0, "included": True,
                }],
                "selected_equipment": [{
                    "id": 3, "name": "Tables", "price": 0, "qty": 2,
                    "duration_qty": 1, "unit": "piece", "subtotal": 0, "included": True,
                }],
                "food_removal_credit": 0,
            },
        },
    )

    quotation = quotation_service._create_customizable_quotation(
        QuotationWriteDatabase(), booking, 30
    )

    assert quotation.total_amount == 1410
    assert quotation.package_details["menu_extras_total"] == 160
    assert quotation.package_details["selected_menu_extras"][0]["qty"] == 2
    assert quotation.package_details["selected_food"][0]["replacement_for_name"] == "Chicken"
    assert quotation.package_details["selected_services"][0]["included"] is True
    assert quotation.package_details["selected_equipment"][0]["included"] is True
