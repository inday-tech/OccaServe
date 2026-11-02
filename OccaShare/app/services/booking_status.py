from typing import Dict


_PAYMENT_REVIEW_STATUSES = {
    "proof_submitted",
    "balance_proof_submitted",
    "cash_payment_requested",
    "cash_balance_requested",
    "pending_verification",
}
_PAYMENT_COMPLETE_STATUSES = {
    "deposit_paid",
    "partially_paid",
    "paid",
    "fully_paid",
    "verified",
    "confirmed",
}
_PARTIAL_PAYMENT_STATUSES = {
    "deposit_paid",
    "partially_paid",
    "partial",
    "partial_paid",
    "downpayment_paid",
}
_REUPLOAD_STATUSES = {"reupload_requested", "balance_reupload_requested"}

_STATUS_PRESENTATION = {
    "draft": ("Draft", "draft", "Continue your booking", "No action until the customer continues"),
    "pending_review": ("Waiting for caterer review", "pending", "Wait for the caterer's review", "Review the booking request"),
    "under_review": ("Waiting for caterer review", "pending", "Wait for the caterer's review", "Review the booking request"),
    "inquiry": ("Quotation being prepared", "pending", "Wait for the quotation", "Prepare and send the quotation"),
    "pending_quotation": ("Quotation sent", "pending", "Review the quotation and choose a deposit", "Wait for the customer to review the quotation"),
    "quoted": ("Quotation sent", "pending", "Review the quotation and choose a deposit", "Wait for the customer to review the quotation"),
    "quotation_phase": ("Quotation sent", "pending", "Review the quotation and choose a deposit", "Wait for the customer to review the quotation"),
    "awaiting_caterer": ("Agreement awaiting caterer", "pending", "Wait for the caterer's signature", "Review and sign the agreement"),
    "awaiting_customer": ("Agreement awaiting customer", "pending", "Review and sign the agreement", "Wait for the customer's signature"),
    "pending_payment": ("Payment due", "pay-now", "Complete the requested payment", "Wait for the customer's payment"),
    "awaiting_payment": ("Payment due", "pay-now", "Complete the requested payment", "Wait for the customer's payment"),
    "pending": ("Payment due", "pay-now", "Complete the requested payment", "Wait for the customer's payment"),
    "confirmed": ("Confirmed", "confirmed", "Check the booking and event updates", "Coordinate event details with the customer"),
    "tentative": ("Tentative", "pending", "Wait for the caterer to confirm the booking", "Confirm the booking details"),
    "preparing": ("Preparing", "preparing", "Check the preparation update", "Update the preparation status"),
    "ready_for_delivery": ("Ready for delivery", "active", "Check the delivery update", "Update delivery progress"),
    "ready_for_pickup": ("Ready for pickup", "active", "Coordinate pickup with the caterer", "Coordinate pickup with the customer"),
    "on_the_way": ("On the way", "active", "Check the delivery update", "Update the customer on delivery progress"),
    "arrived": ("Arrived", "active", "Check the event setup update", "Begin or update event setup"),
    "setup_ongoing": ("Event setup", "active", "Check the event setup update", "Update event setup progress"),
    "setup_in_progress": ("Event setup", "active", "Check the event setup update", "Update event setup progress"),
    "ready_for_event": ("Ready for event", "active", "Check the event update", "Update the event progress"),
    "in_progress": ("Event in progress", "active", "Check the event update", "Mark the event complete when finished"),
    "completed": ("Completed", "completed", "Leave a review for the caterer", "No further action required"),
    "delivered": ("Completed", "completed", "Leave a review for the caterer", "No further action required"),
    "released": ("Equipment released", "active", "Follow the return instructions", "Inspect returned equipment"),
    "cancelled": ("Cancelled", "cancelled", "No further action required", "No further action required"),
    "rejected": ("Declined", "cancelled", "No further action required", "No further action required"),
    "expired": ("Expired", "cancelled", "No further action required", "No further action required"),
    "no_show": ("No show", "cancelled", "Contact the caterer if you need help", "Review the booking record"),
}

_PREPARATION_PRESENTATION = {
    "preparing": "preparing",
    "ready_for_delivery": "ready_for_delivery",
    "ready_for_pickup": "ready_for_pickup",
    "on_the_way": "on_the_way",
    "arrived": "arrived",
    "setup_in_progress": "setup_in_progress",
    "ready_for_event": "ready_for_event",
    "in_progress": "in_progress",
    "completed": "completed",
}
_CONFIRMED_PREPARATION_STATUSES = {
    "preparing", "ready_for_delivery", "on_the_way", "arrived",
    "setup_in_progress", "ready_for_event", "in_progress", "completed",
}


def booking_status_display(
    status: str,
    payment_status: str = "",
    preparation_status: str = "",
    payment_under_review: bool = False,
) -> Dict[str, str]:
    """Return one canonical booking status and role-specific next steps."""
    booking_status = (status or "").strip().lower()
    payment = (payment_status or "").strip().lower()
    preparation = (preparation_status or "").strip().lower()

    if payment in _REUPLOAD_STATUSES:
        return {
            "label": "Payment proof needs re-upload",
            "tone": "reupload",
            "customer_action": "Upload a corrected payment proof",
            "caterer_action": "Wait for the customer to re-upload payment proof",
        }
    if payment_under_review or payment in _PAYMENT_REVIEW_STATUSES:
        if payment in {"balance_proof_submitted", "cash_balance_requested"}:
            caterer_action = "Verify the balance payment"
        elif payment == "cash_payment_requested":
            caterer_action = "Confirm the cash payment"
        else:
            caterer_action = "Verify the submitted payment"
        return {
            "label": "Payment under review",
            "tone": "pending",
            "customer_action": "Wait for the caterer to verify payment",
            "caterer_action": caterer_action,
        }

    if booking_status in {"pending_payment", "awaiting_payment", "pending"}:
        if payment in _PARTIAL_PAYMENT_STATUSES:
            return {
                "label": "Partially paid",
                "tone": "pay-now",
                "customer_action": "Complete the remaining requested payment",
                "caterer_action": "Wait for the customer's remaining payment",
            }
        if payment in _PAYMENT_COMPLETE_STATUSES:
            return {
                "label": "Payment received",
                "tone": "confirmed",
                "customer_action": "Wait for the booking update",
                "caterer_action": "Review the booking and update its progress",
            }

    effective_status = booking_status
    if booking_status == "confirmed" and preparation in _CONFIRMED_PREPARATION_STATUSES:
        effective_status = _PREPARATION_PRESENTATION[preparation]
    presentation = _STATUS_PRESENTATION.get(effective_status)
    if presentation:
        label, tone, customer_action, caterer_action = presentation
    else:
        label = booking_status.replace("_", " ").title() if booking_status else "Unknown"
        tone = "draft"
        customer_action = "Check the booking details"
        caterer_action = "Review the booking details"
    return {
        "label": label,
        "tone": tone,
        "customer_action": customer_action,
        "caterer_action": caterer_action,
    }


def customer_booking_status_display(
    status: str,
    payment_status: str = "",
    preparation_status: str = "",
    has_review: bool = False,
    payment_under_review: bool = False,
) -> Dict[str, str]:
    """Return the shared status plus the next step for the customer."""
    display = booking_status_display(
        status,
        payment_status,
        preparation_status,
        payment_under_review,
    )
    if has_review and (status or "").strip().lower() in {"completed", "delivered"}:
        display["customer_action"] = "Your review has been submitted"
    return display
