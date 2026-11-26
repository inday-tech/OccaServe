"""Tests for the unified booking fulfillment lifecycle.

Covers the dead-end fix: preparation_status is the source of truth and
booking.status is derived/synced from it through PREP_STATUSES.
"""
from types import SimpleNamespace

from app.services.booking_status import booking_status_display
from app.services.preparation_service import (
    PREP_STATUSES,
    completion_stage_block_reason,
    derive_booking_status,
    normalize_prep_status,
    preparation_options,
    preparation_transition_error,
    sync_booking_status_from_preparation,
)


def _booking(status, preparation_status="not_started", **kwargs):
    base = dict(
        status=status,
        preparation_status=preparation_status,
        document_type="booking",
        is_archived=False,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _pay(can_start=True, can_complete=True):
    return {"can_start_preparation": can_start, "can_mark_completed": can_complete}


# ---------------------------------------------------------------------------
# derive_booking_status
# ---------------------------------------------------------------------------

def test_derive_keeps_status_without_preparation():
    assert derive_booking_status("confirmed", "") == "confirmed"
    assert derive_booking_status("confirmed", "not_started") == "confirmed"


def test_derive_promotes_confirmed_to_preparation_stage():
    assert derive_booking_status("confirmed", "preparing") == "preparing"
    assert derive_booking_status("confirmed", "setup_in_progress") == "setup_ongoing"


def test_derive_shows_event_day_stages():
    assert derive_booking_status("setup_ongoing", "ready_for_event") == "ready_for_event"
    assert derive_booking_status("setup_ongoing", "post_event_cleanup") == "post_event_cleanup"
    assert derive_booking_status("ready_for_event", "post_event_cleanup") == "post_event_cleanup"


def test_derive_never_moves_backward():
    assert derive_booking_status("on_the_way", "ready_for_delivery") == "on_the_way"
    assert derive_booking_status("arrived", "ready_for_delivery") == "arrived"
    assert derive_booking_status("completed", "preparing") == "completed"


def test_derive_preserves_pickup_status():
    assert derive_booking_status("ready_for_pickup", "ready_for_delivery") == "ready_for_pickup"


def test_derive_does_not_override_terminal_or_pre_fulfillment():
    assert derive_booking_status("cancelled", "preparing") == "cancelled"
    assert derive_booking_status("awaiting_payment", "preparing") == "awaiting_payment"
    assert derive_booking_status("pending_review", "completed") == "pending_review"


def test_derive_handles_legacy_preparation_values():
    assert derive_booking_status("confirmed", "setup_ongoing") == "setup_ongoing"
    assert derive_booking_status("confirmed", "arrived") == "arrived"
    assert derive_booking_status("confirmed", "in_preparation") == "preparing"


# ---------------------------------------------------------------------------
# sync_booking_status_from_preparation
# ---------------------------------------------------------------------------

def test_sync_promotes_confirmed_to_preparing():
    booking = _booking("confirmed", "preparing")
    assert sync_booking_status_from_preparation(booking) is True
    assert booking.status == "preparing"


def test_sync_reaches_on_site_stages_that_were_previously_unreachable():
    booking = _booking("arrived", "setup_in_progress")
    assert sync_booking_status_from_preparation(booking) is True
    assert booking.status == "setup_ongoing"

    booking = _booking("setup_ongoing", "ready_for_event")
    assert sync_booking_status_from_preparation(booking) is True
    assert booking.status == "ready_for_event"


def test_sync_keeps_ready_for_event_through_cleanup():
    booking = _booking("ready_for_event", "post_event_cleanup")
    assert sync_booking_status_from_preparation(booking) is False
    assert booking.status == "ready_for_event"


def test_sync_never_regresses_or_overrides_terminal():
    pickup = _booking("ready_for_pickup", "ready_for_delivery")
    assert sync_booking_status_from_preparation(pickup) is False
    assert pickup.status == "ready_for_pickup"

    transit = _booking("on_the_way", "ready_for_delivery")
    assert sync_booking_status_from_preparation(transit) is False
    assert transit.status == "on_the_way"

    done = _booking("completed", "preparing")
    assert sync_booking_status_from_preparation(done) is False
    assert done.status == "completed"

    unpaid_stage = _booking("awaiting_payment", "preparing")
    assert sync_booking_status_from_preparation(unpaid_stage) is False
    assert unpaid_stage.status == "awaiting_payment"


# ---------------------------------------------------------------------------
# preparation_transition_error (single source of truth for the endpoint)
# ---------------------------------------------------------------------------

def test_on_site_booking_can_walk_the_full_preparation_ladder():
    """Regression test for the dead-end: every on-site stage must be reachable."""
    booking = _booking("confirmed", "not_started")

    # confirmed -> preparing (deposit verified)
    assert preparation_transition_error(booking, "preparing", _pay()) is None
    booking.preparation_status = "preparing"
    sync_booking_status_from_preparation(booking)
    assert booking.status == "preparing"

    # preparing -> ready_for_delivery is owned by dispatch proof
    err = preparation_transition_error(booking, "ready_for_delivery", _pay())
    assert err is not None and err[0] == 409

    # simulate packed + dispatched + arrived
    booking.preparation_status = "ready_for_delivery"
    booking.status = "arrived"

    # arrived -> setup_in_progress -> ready_for_event -> post_event_cleanup
    assert preparation_transition_error(booking, "setup_in_progress", _pay()) is None
    booking.preparation_status = "setup_in_progress"
    sync_booking_status_from_preparation(booking)
    assert booking.status == "setup_ongoing"

    assert preparation_transition_error(booking, "ready_for_event", _pay()) is None
    booking.preparation_status = "ready_for_event"
    sync_booking_status_from_preparation(booking)
    assert booking.status == "ready_for_event"

    assert preparation_transition_error(booking, "post_event_cleanup", _pay()) is None
    booking.preparation_status = "post_event_cleanup"

    # completion gates now pass for a non-invoice booking
    assert completion_stage_block_reason(booking) is None
    assert preparation_transition_error(booking, "completed", _pay()) is not None


def test_setup_in_progress_requires_arrived_booking_status():
    booking = _booking("on_the_way", "ready_for_delivery")
    err = preparation_transition_error(booking, "setup_in_progress", _pay())
    assert err is not None and "arrived" in err[1]


def test_ready_for_event_requires_setup_stage_and_booking_status():
    # right prep stage but booking.status not yet synced
    booking = _booking("arrived", "setup_in_progress")
    err = preparation_transition_error(booking, "ready_for_event", _pay())
    assert err is not None

    # right booking.status but wrong prep stage
    booking = _booking("setup_ongoing", "ready_for_delivery")
    err = preparation_transition_error(booking, "ready_for_event", _pay())
    assert err is not None


def test_cannot_skip_or_move_backward():
    booking = _booking("confirmed", "not_started")
    err = preparation_transition_error(booking, "ready_for_event", _pay())
    assert err is not None and err[0] == 409

    booking = _booking("preparing", "preparing")
    err = preparation_transition_error(booking, "not_started", _pay())
    assert err is not None and err[0] == 400


def test_preparing_requires_verified_deposit():
    booking = _booking("confirmed", "not_started")
    err = preparation_transition_error(booking, "preparing", _pay(can_start=False))
    assert err is not None and err[0] == 409
    assert preparation_transition_error(booking, "preparing", _pay(can_start=True)) is None


def test_terminal_and_unaccepted_bookings_rejected():
    for status in ("cancelled", "completed", "expired", "delivered"):
        booking = _booking(status, "not_started")
        err = preparation_transition_error(booking, "preparing", _pay())
        assert err is not None and err[0] == 400

    booking = _booking("awaiting_payment", "not_started")
    err = preparation_transition_error(booking, "preparing", _pay())
    assert err is not None and err[0] == 409

    booking = _booking("confirmed", "not_started", is_archived=True)
    err = preparation_transition_error(booking, "preparing", _pay())
    assert err is not None and err[0] == 400


def test_same_stage_is_a_no_op_success():
    booking = _booking("preparing", "preparing")
    assert preparation_transition_error(booking, "preparing", _pay()) is None


# ---------------------------------------------------------------------------
# preparation_options (backend-driven UI)
# ---------------------------------------------------------------------------

def test_options_expose_only_adjacent_stage_with_reasons():
    booking = _booking("confirmed", "not_started")
    options = preparation_options(booking, _pay())
    by_key = {o["key"]: o for o in options}

    assert by_key["not_started"]["allowed"] is True   # current stage
    assert by_key["preparing"]["allowed"] is True     # next stage
    assert by_key["setup_in_progress"]["allowed"] is False
    assert by_key["setup_in_progress"]["reason"]
    assert by_key["completed"]["allowed"] is False
    assert by_key["ready_for_delivery"]["allowed"] is False  # needs dispatch proof


def test_options_reflect_arrived_booking():
    booking = _booking("arrived", "ready_for_delivery")
    options = preparation_options(booking, _pay())
    by_key = {o["key"]: o for o in options}
    assert by_key["setup_in_progress"]["allowed"] is True
    assert by_key["ready_for_event"]["allowed"] is False


# ---------------------------------------------------------------------------
# booking_status_display uses the derived status
# ---------------------------------------------------------------------------

def test_display_uses_derived_status_for_event_day():
    display = booking_status_display("arrived", "paid", "setup_in_progress")
    assert display["label"] == "Event setup"
    assert display["tone"] == "active"

    display = booking_status_display("ready_for_event", "paid", "post_event_cleanup")
    assert display["label"] == "Post-event cleanup"


def test_display_still_prefers_pickup_over_delivery_preparation():
    display = booking_status_display("ready_for_pickup", "paid", "ready_for_delivery")
    assert display["label"] == "Ready for pickup"


# ---------------------------------------------------------------------------
# PREP_STATUSES booking_status mapping is complete enough to sync
# ---------------------------------------------------------------------------

def test_prep_booking_status_mapping_covers_sync_stages():
    by_key = {s["key"]: s for s in PREP_STATUSES}
    assert by_key["preparing"]["booking_status"] == "preparing"
    assert by_key["setup_in_progress"]["booking_status"] == "setup_ongoing"
    assert by_key["ready_for_event"]["booking_status"] == "ready_for_event"
    # post_event_cleanup intentionally keeps booking.status at ready_for_event
    assert by_key["post_event_cleanup"]["booking_status"] is None
    assert by_key["completed"]["booking_status"] is None


def test_normalize_prep_status_unchanged_for_legacy_values():
    assert normalize_prep_status("scheduled", "confirmed") == "not_started"
    assert normalize_prep_status("in_preparation", "confirmed") == "preparing"
    assert normalize_prep_status("setup_ongoing", "arrived") == "setup_in_progress"
