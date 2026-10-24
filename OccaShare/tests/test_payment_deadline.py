from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.payment_deadline import (
    activate_initial_payment_request,
    booking_is_extension_eligible,
    expire_initial_payment_if_due,
    normalize_deadline_hours,
)


class FakeDatabase:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1


def make_booking(hours=24):
    return SimpleNamespace(
        id=17,
        status="awaiting_payment",
        payment_status="pending",
        payment_request_status="pending",
        payment_request_activated_at=None,
        payment_deadline_at=None,
        payment_deadline_hours_snapshot=None,
        event_date=datetime.now(timezone.utc).date() + timedelta(days=30),
        caterer=SimpleNamespace(payment_deadline_hours=hours),
        quotation=SimpleNamespace(status="signed", customer_signed_at=None, caterer_signed_at=None),
    )


def test_activation_snapshots_caterer_deadline_and_is_idempotent():
    now = datetime(2026, 10, 24, 7, 0, tzinfo=timezone.utc)
    booking = make_booking(72)

    assert activate_initial_payment_request(booking, now=now)
    assert booking.payment_deadline_hours_snapshot == 72
    assert booking.payment_request_activated_at == now
    assert booking.payment_deadline_at == now + timedelta(hours=72)

    booking.caterer.payment_deadline_hours = 24
    assert not activate_initial_payment_request(booking, now=now + timedelta(hours=1))
    assert booking.payment_deadline_hours_snapshot == 72
    assert booking.payment_deadline_at == now + timedelta(hours=72)


def test_activation_requires_finalized_agreement_and_eligible_booking():
    booking = make_booking()
    booking.quotation.status = "awaiting_caterer"
    assert not activate_initial_payment_request(booking)
    booking.quotation.status = "signed"
    booking.status = "cancelled"
    assert not activate_initial_payment_request(booking)


def test_deadline_options_reject_unapproved_values():
    assert normalize_deadline_hours(24) == 24
    assert normalize_deadline_hours("72") == 72
    assert normalize_deadline_hours(12) == 48
    assert normalize_deadline_hours("invalid") == 48


def test_expiration_is_server_side_and_retains_booking_history():
    booking = make_booking()
    now = datetime.now(timezone.utc)
    booking.payment_deadline_at = now - timedelta(seconds=1)
    db = FakeDatabase()

    assert expire_initial_payment_if_due(db, booking, now=now)
    assert booking.status == "awaiting_payment"
    assert booking.payment_status == "expired"
    assert booking.payment_request_status == "expired"
    assert db.commits == 1
    assert "retained" in db.added[0].notes
    assert not expire_initial_payment_if_due(db, booking, now=now)
    assert db.commits == 1


def test_expiration_does_not_override_payment_already_in_progress():
    booking = make_booking()
    booking.payment_deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
    booking.payment_status = "proof_submitted"
    db = FakeDatabase()

    assert not expire_initial_payment_if_due(db, booking)
    assert booking.payment_status == "proof_submitted"
    assert db.commits == 0


def test_extension_requires_signed_agreement_future_event_and_unpaid_state():
    booking = make_booking()
    assert booking_is_extension_eligible(booking)[0]
    booking.payment_status = "proof_submitted"
    assert not booking_is_extension_eligible(booking)[0]
    booking.payment_status = "expired"
    booking.event_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    assert not booking_is_extension_eligible(booking)[0]
