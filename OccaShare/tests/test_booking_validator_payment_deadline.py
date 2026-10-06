from datetime import date, datetime, timedelta
from types import SimpleNamespace

from app.services.booking_validator import BookingValidator


class EmptyQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
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
    )


def test_confirmed_balance_payment_ignores_old_booking_deadline():
    booking = make_confirmed_booking(date.today())

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
        ignore_booking_deadline=True,
    )

    assert is_valid is True
    assert message == "Booking is valid."


def test_balance_payment_still_rejected_after_event_date():
    booking = make_confirmed_booking(date.today() - timedelta(days=1))

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
        ignore_booking_deadline=True,
    )

    assert is_valid is False
    assert "event date has already passed" in message
    assert booking.status == "expired"


def test_other_payment_flows_still_honor_booking_deadline():
    booking = make_confirmed_booking(date.today() + timedelta(days=1))

    is_valid, message = BookingValidator.validate_booking_state(
        EmptyDatabase(),
        booking,
    )

    assert is_valid is False
    assert "booking has expired" in message
    assert booking.status == "expired"
