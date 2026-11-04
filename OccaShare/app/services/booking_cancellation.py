from datetime import datetime, time
from zoneinfo import ZoneInfo

from .payment_service import PaymentService


CANCELLATION_POLICY_VERSION = "2026-11-v1"
CANCELLATION_REFUND_TIERS = (
    (30, 100.0),
    (15, 75.0),
    (7, 50.0),
    (0, 0.0),
)
CANCELLATION_POLICY_TEXT = (
    "Customer cancellation requests are reviewed by the caterer. For requests made "
    "30 or more days before the event, the estimated refund is 100% of verified "
    "payments; 15–29 days, 75%; 7–14 days, 50%; under 7 days, 0%. Unverified "
    "payment proofs and cash not yet received are excluded. Cancellation is not "
    "effective until the caterer approves the request."
)
MANILA = ZoneInfo("Asia/Manila")


def event_has_started(booking, now=None):
    if not booking.event_date:
        return True
    start_time = booking.event_time or time.min
    event_start = datetime.combine(booking.event_date, start_time, tzinfo=MANILA)
    return (now or datetime.now(MANILA)) >= event_start


def refund_percent_for_booking(booking, requested_at=None):
    if not booking.event_date:
        return 0.0
    now = requested_at or datetime.now(MANILA)
    local_today = now.astimezone(MANILA).date() if now.tzinfo else now.date()
    days_before_event = (booking.event_date - local_today).days
    for minimum_days, percentage in CANCELLATION_REFUND_TIERS:
        if days_before_event >= minimum_days:
            return percentage
    return 0.0


def verified_paid_amount(booking):
    return round(float(PaymentService.get_payment_summary(booking).get("verified_paid") or 0), 2)


def estimate_refund(booking, requested_at=None):
    paid = verified_paid_amount(booking)
    percentage = refund_percent_for_booking(booking, requested_at)
    return {
        "verified_paid_amount": paid,
        "refund_percent": percentage,
        "estimated_refund_amount": round(paid * percentage / 100, 2),
    }


def format_refund_policy():
    return {
        "version": CANCELLATION_POLICY_VERSION,
        "text": CANCELLATION_POLICY_TEXT,
        "tiers": [
            {"minimum_days": days, "percentage": percentage}
            for days, percentage in CANCELLATION_REFUND_TIERS
        ],
    }
