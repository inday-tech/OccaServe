from app.routers.chat import _walk_in_only_customer_ids
from app.db import models


class BookingQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class BookingDatabase:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *columns):
        assert columns == (
            models.Booking.user_id,
            models.Booking.custom_requirements,
            models.Booking.booking_source,
        )
        return BookingQuery(self.rows)


def test_walkin_only_customer_is_hidden_but_customer_with_online_booking_is_kept():
    db = BookingDatabase([
        (1, {"is_walk_in": True}, "OccaServe"),
        (2, {"is_walk_in": True}, "OccaServe"),
        (2, {}, "OccaServe"),
        (3, {}, "OccaServe"),
    ])

    assert _walk_in_only_customer_ids(db, 10, [1, 2, 3]) == {1}


def test_walkin_booking_source_is_recognized_without_custom_flag():
    db = BookingDatabase([
        (4, {}, "Walk-in"),
        (5, {}, "manual"),
    ])

    assert _walk_in_only_customer_ids(db, 10, [4, 5]) == {4, 5}
