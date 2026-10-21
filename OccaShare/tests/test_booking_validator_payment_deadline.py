from datetime import date, datetime, timedelta
from types import SimpleNamespace

from app.services.booking_validator import BookingValidator


class EmptyQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None

    def get(self, _record_id):
        return None


class EmptyDatabase:
    def query(self, _model):
        return EmptyQuery()

    def add(self, _record):
        pass

    def commit(self):
        pass


def make_confirmed_booking(event_date):
    return SimpleNamespace(
        id=1,
        status="confirmed",
        event_date=event_date,
        expires_at=datetime.now() - timedelta(hours=1),
        caterer_id=1,
        caterer_notes=None,
        payment_status="deposit_paid",
    )


def test_confirmed_balance_payment_ignores_automatic_booking_deadline():
    booking = make_confirmed_booking(date.today())

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
        ignore_booking_deadline=True,
    )

    assert is_valid is True
    assert message == "Booking is valid."


def test_balance_payment_is_allowed_after_event_date():
    booking = make_confirmed_booking(date.today() - timedelta(days=1))

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
    )

    assert is_valid is True
    assert message == "Booking is valid."
    assert booking.status == "confirmed"


def test_event_day_payment_request_is_not_expired_by_lead_time():
    booking = make_confirmed_booking(date.today())
    booking.status = "pending"
    booking.payment_status = "cash_payment_requested"

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
    )

    assert is_valid is True
    assert message == "Booking is valid."
    assert booking.status == "pending"


def test_confirmed_booking_is_not_expired_by_old_payment_deadline():
    booking = make_confirmed_booking(date.today() + timedelta(days=1))

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
    )

    assert is_valid is True
    assert message == "Booking is valid."
    assert booking.status == "confirmed"


def test_only_unfinished_drafts_honor_draft_expiration():
    booking = make_confirmed_booking(date.today() + timedelta(days=1))
    booking.status = "draft"
    booking.payment_status = "pending"

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
    )

    assert is_valid is False
    assert "booking has expired" in message
    assert booking.status == "expired"


def test_inquiry_is_expired_when_event_date_has_passed_before_agreement_signing():
    booking = make_confirmed_booking(date.today() - timedelta(days=1))
    booking.status = "inquiry"
    booking.payment_status = "pending"

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
    )

    assert is_valid is False
    assert "event date has already passed" in message
    assert booking.status == "expired"
