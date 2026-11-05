from datetime import datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.services.booking_cancellation import cancellation_mode_for_booking
from app.services.preparation_service import PREP_STATUSES


MANILA = ZoneInfo("Asia/Manila")
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=MANILA)


@pytest.mark.parametrize(
    ("preparation_status", "expected_mode"),
    [
        ("not_started", "cancel"),
        ("preparing", "request"),
        ("ready_for_delivery", "request"),
        ("setup_in_progress", None),
        ("ready_for_event", None),
        ("post_event_cleanup", None),
        ("completed", None),
    ],
)
def test_customer_cancellation_eligibility_for_all_preparation_stages(
    preparation_status, expected_mode
):
    booking = SimpleNamespace(
        status="confirmed",
        preparation_status=preparation_status,
        event_date=NOW.date() + timedelta(days=10),
        event_time=None,
    )

    assert cancellation_mode_for_booking(booking, NOW) == expected_mode


def test_cancellation_rules_cover_the_existing_seven_preparation_stages():
    assert [stage["key"] for stage in PREP_STATUSES] == [
        "not_started",
        "preparing",
        "ready_for_delivery",
        "setup_in_progress",
        "ready_for_event",
        "post_event_cleanup",
        "completed",
    ]


@pytest.mark.parametrize("booking_status", ["cancelled", "completed", "draft", "expired"])
def test_inactive_booking_status_never_allows_customer_cancellation(booking_status):
    booking = SimpleNamespace(
        status=booking_status,
        preparation_status="not_started",
        event_date=NOW.date() + timedelta(days=10),
        event_time=None,
    )

    assert cancellation_mode_for_booking(booking, NOW) is None


def test_event_cutoff_blocks_cancellation_even_before_setup():
    booking = SimpleNamespace(
        status="confirmed",
        preparation_status="not_started",
        event_date=NOW.date(),
        event_time=time(10, 0),
    )

    assert cancellation_mode_for_booking(booking, NOW) is None


def test_unknown_preparation_status_fails_closed():
    booking = SimpleNamespace(
        status="confirmed",
        preparation_status="unexpected_stage",
        event_date=NOW.date() + timedelta(days=10),
        event_time=None,
    )

    assert cancellation_mode_for_booking(booking, NOW) is None
