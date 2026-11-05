from datetime import datetime, time
from zoneinfo import ZoneInfo

from .preparation_service import PREP_STATUSES, PREP_STATUS_KEYS, normalize_prep_status


MANILA = ZoneInfo("Asia/Manila")
CANCELLATION_POLICY_VERSION = "2026-11-no-refund-v1"
CANCELLATION_POLICY_TEXT = (
    "Customer-initiated booking cancellations are not refundable. Before preparation "
    "starts, a booking may be cancelled directly, including while a quotation or signed "
    "agreement is awaiting payment. During preparation or after preparation is complete, "
    "the customer may request cancellation for caterer review. Cancellation is not "
    "available once Setup in Progress begins or after the event cutoff."
)
ACTIVE_BOOKING_STATUSES = {
    "draft",
    "pending_review",
    "under_review",
    "inquiry",
    "pending_quotation",
    "quoted",
    "quotation_phase",
    "awaiting_caterer",
    "awaiting_customer",
    "pending_payment",
    "awaiting_payment",
    "pending",
    "tentative",
    "confirmed",
    "preparing",
    "ready_for_delivery",
    "ready_for_pickup",
    "on_the_way",
    "arrived",
    "setup_ongoing",
    "in_progress",
    "ready_for_event",
}
LEGACY_PREPARATION_STATUSES = {
    "scheduled",
    "in_preparation",
    "ready",
    "ready_for_pickup",
    "setup_ongoing",
    "arrived",
    "in_progress",
}


def event_has_started(booking, now=None):
    if not booking.event_date:
        return True
    start_time = booking.event_time or time.min
    event_start = datetime.combine(booking.event_date, start_time, tzinfo=MANILA)
    return (now or datetime.now(MANILA)) >= event_start


def cancellation_mode_for_booking(booking, now=None):
    """Return cancel, request, or None based on lifecycle, preparation, and event cutoff."""
    booking_status = (booking.status or "").strip().lower()
    if booking_status not in ACTIVE_BOOKING_STATUSES or event_has_started(booking, now):
        return None

    raw_preparation = (booking.preparation_status or "").strip().lower()
    if raw_preparation and raw_preparation not in PREP_STATUS_KEYS | LEGACY_PREPARATION_STATUSES:
        return None
    preparation = normalize_prep_status(raw_preparation, booking_status)
    stage_order = [stage["key"] for stage in PREP_STATUSES]
    stage_index = stage_order.index(preparation)
    if stage_index == 0:
        return "cancel"
    if preparation in {"preparing", "ready_for_delivery"}:
        return "request"
    return None


def format_cancellation_policy():
    return {
        "version": CANCELLATION_POLICY_VERSION,
        "text": CANCELLATION_POLICY_TEXT,
    }
