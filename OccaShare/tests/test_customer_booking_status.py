import pytest

from app.services.booking_status import customer_booking_status_display


@pytest.mark.parametrize(
    ("status", "payment_status", "expected_label", "expected_tone"),
    [
        ("pending_review", "pending", "Waiting for Caterer Review", "pending"),
        ("inquiry", "pending", "Quotation being prepared", "pending"),
        ("pending_quotation", "pending", "Quotation sent", "pending"),
        ("awaiting_caterer", "pending", "Agreement awaiting caterer", "pending"),
        ("awaiting_customer", "pending", "Agreement awaiting customer", "pending"),
        ("awaiting_payment", "pending", "Payment due", "pay-now"),
        ("awaiting_payment", "paid", "Payment received", "confirmed"),
        ("confirmed", "proof_submitted", "Payment under review", "pending"),
        ("confirmed", "reupload_requested", "Payment proof needs re-upload", "reupload"),
        ("pending", "deposit_paid", "Partially paid", "pay-now"),
        ("pending", "paid", "Payment received", "confirmed"),
        ("confirmed", "paid", "Confirmed", "confirmed"),
        ("tentative", "deposit_paid", "Tentative", "pending"),
        ("preparing", "paid", "Preparing", "preparing"),
        ("ready_for_delivery", "paid", "Ready for delivery", "active"),
        ("ready_for_pickup", "paid", "Ready for pickup", "active"),
        ("on_the_way", "paid", "On the way", "active"),
        ("arrived", "paid", "Arrived", "active"),
        ("setup_ongoing", "paid", "Event setup", "active"),
        ("in_progress", "paid", "Event in progress", "active"),
        ("completed", "paid", "Completed", "completed"),
        ("delivered", "paid", "Completed", "completed"),
        ("released", "deposit_paid", "Equipment released", "active"),
        ("cancelled", "pending", "Cancelled", "cancelled"),
        ("rejected", "pending", "Declined", "cancelled"),
        ("expired", "pending", "Expired", "cancelled"),
        ("no_show", "pending", "No show", "cancelled"),
    ],
)
def test_customer_booking_status_matches_bookings_page(
    status, payment_status, expected_label, expected_tone
):
    display = customer_booking_status_display(status, payment_status)
    assert display["label"].lower() == expected_label.lower()
    assert display["tone"] == expected_tone
    assert display["customer_action"]
    assert display["caterer_action"]


def test_unknown_status_is_normalized_for_customer_display():
    display = customer_booking_status_display("  custom_status  ", "")
    assert display["label"] == "Custom Status"
    assert display["tone"] == "draft"


def test_preparation_progress_uses_the_same_status_for_both_roles():
    customer_display = customer_booking_status_display(
        "confirmed", "paid", "setup_in_progress"
    )
    caterer_display = customer_booking_status_display(
        "confirmed", "paid", "setup_in_progress"
    )

    assert customer_display["label"] == caterer_display["label"] == "Event setup"
    assert customer_display["customer_action"] == "Check the event setup update"
    assert caterer_display["caterer_action"] == "Update event setup progress"


def test_pickup_status_is_not_overridden_by_delivery_preparation_flag():
    display = customer_booking_status_display(
        "ready_for_pickup", "paid", "ready_for_delivery"
    )

    assert display["label"] == "Ready for pickup"


def test_payment_review_status_keeps_each_role_action_clear():
    display = customer_booking_status_display("confirmed", "balance_proof_submitted")

    assert display["label"] == "Payment under review"
    assert display["customer_action"] == "Wait for the caterer to verify payment"
    assert display["caterer_action"] == "Verify the balance payment"


def test_derived_payment_review_overrides_stale_booking_payment_flag():
    display = customer_booking_status_display(
        "confirmed",
        "paid",
        payment_under_review=True,
    )

    assert display["label"] == "Payment under review"


def test_completed_booking_does_not_prompt_for_a_duplicate_review():
    display = customer_booking_status_display("completed", "paid", has_review=True)

    assert display["customer_action"] == "Your review has been submitted"
