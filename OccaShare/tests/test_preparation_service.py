from types import SimpleNamespace

from app.services.preparation_service import (
    build_prep_summary,
    completion_stage_block_reason,
)


def test_ready_preparation_status_uses_event_catering_label():
    booking = SimpleNamespace(
        preparation_status="ready_for_delivery",
        status="ready_for_delivery",
        updated_at=None,
        created_at=None,
    )

    summary = build_prep_summary(booking)

    assert summary["label"] == "Preparation Complete"
    assert next(
        status["label"]
        for status in summary["statuses"]
        if status["key"] == "ready_for_delivery"
    ) == "Preparation Complete"


def test_post_event_cleanup_is_the_stage_between_ready_and_completed():
    booking = SimpleNamespace(
        preparation_status="post_event_cleanup",
        status="setup_ongoing",
        updated_at=None,
        created_at=None,
    )

    summary = build_prep_summary(booking)

    assert summary["label"] == "Post-Event Cleanup"
    assert [status["key"] for status in summary["statuses"]][-3:] == [
        "ready_for_event",
        "post_event_cleanup",
        "completed",
    ]


def test_event_completion_requires_post_event_cleanup():
    booking = SimpleNamespace(
        preparation_status="ready_for_event",
        status="setup_ongoing",
        document_type="booking",
    )

    assert completion_stage_block_reason(booking) == (
        "Complete the Post-Event Cleanup checklist before marking this event completed."
    )
    booking.preparation_status = "post_event_cleanup"
    assert completion_stage_block_reason(booking) is None


def test_legacy_ready_for_event_booking_can_complete_after_cleanup():
    booking = SimpleNamespace(
        preparation_status="post_event_cleanup",
        status="ready_for_event",
        document_type="booking",
    )

    assert completion_stage_block_reason(booking) is None


def test_pickup_and_food_order_completion_do_not_require_event_cleanup():
    pickup_booking = SimpleNamespace(
        preparation_status="not_started",
        status="ready_for_pickup",
        document_type="booking",
    )
    food_order = SimpleNamespace(
        preparation_status="not_started",
        status="setup_ongoing",
        document_type="invoice",
    )

    assert completion_stage_block_reason(pickup_booking) is None
    assert completion_stage_block_reason(food_order) is None
