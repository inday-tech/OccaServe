"""Server-authoritative initial payment deadlines and extension eligibility."""

from datetime import datetime, timedelta, timezone

from app.db import models

ALLOWED_PAYMENT_DEADLINE_HOURS = (24, 48, 72)
DEFAULT_PAYMENT_DEADLINE_HOURS = 48
PHILIPPINE_TIMEZONE = timezone(timedelta(hours=8))
PAYMENT_IN_PROGRESS_STATUSES = {
    "proof_submitted",
    "balance_proof_submitted",
    "reupload_requested",
    "balance_reupload_requested",
    "pending_verification",
    "cash_payment_requested",
    "deposit_paid",
    "partially_paid",
    "cash_balance_requested",
    "paid",
    "fully_paid",
}


def utc_now():
    return datetime.now(timezone.utc)


def format_payment_deadline(value):
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(PHILIPPINE_TIMEZONE).strftime("%B %d, %Y at %I:%M %p PHT")


def normalize_deadline_hours(value):
    try:
        hours = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PAYMENT_DEADLINE_HOURS
    return hours if hours in ALLOWED_PAYMENT_DEADLINE_HOURS else DEFAULT_PAYMENT_DEADLINE_HOURS


def activate_initial_payment_request(booking, now=None):
    """Set the fixed deadline once, when the quotation is fully signed."""
    quotation = getattr(booking, "quotation", None)
    if not quotation or quotation.status != "signed":
        return False
    if booking.status not in {"awaiting_payment", "pending_payment", "pending"}:
        return False
    if booking.payment_request_activated_at and booking.payment_deadline_at:
        return False
    if (booking.payment_status or "").lower() in PAYMENT_IN_PROGRESS_STATUSES:
        return False

    activated_at = now or utc_now()
    hours = normalize_deadline_hours(
        getattr(getattr(booking, "caterer", None), "payment_deadline_hours", None)
    )
    booking.payment_deadline_hours_snapshot = hours
    booking.payment_request_activated_at = activated_at
    booking.payment_deadline_at = activated_at + timedelta(hours=hours)
    booking.payment_request_status = "pending"
    if not booking.payment_status or booking.payment_status in {"pending", "expired"}:
        booking.payment_status = "pending"
    return True


def ensure_initial_payment_request(booking, now=None):
    """Backfill a fixed legacy deadline without restarting its old 48-hour clock."""
    if booking.payment_deadline_at and booking.payment_request_activated_at:
        return False
    quotation = getattr(booking, "quotation", None)
    if not quotation or quotation.status != "signed":
        return False
    signed_times = [
        stamp for stamp in (quotation.customer_signed_at, quotation.caterer_signed_at)
        if stamp is not None
    ]
    activated_at = min(signed_times) if signed_times else (quotation.updated_at or now or utc_now())
    if activated_at.tzinfo is None:
        activated_at = activated_at.replace(tzinfo=timezone.utc)
    # Existing UI counted from the customer's signature, so keep that clock for legacy rows.
    if quotation.customer_signed_at:
        activated_at = quotation.customer_signed_at
        if activated_at.tzinfo is None:
            activated_at = activated_at.replace(tzinfo=timezone.utc)
    booking.payment_deadline_hours_snapshot = DEFAULT_PAYMENT_DEADLINE_HOURS
    booking.payment_request_activated_at = activated_at
    booking.payment_deadline_at = activated_at + timedelta(hours=DEFAULT_PAYMENT_DEADLINE_HOURS)
    booking.payment_request_status = "pending"
    return True


def is_payment_expired(booking, now=None):
    deadline = getattr(booking, "payment_deadline_at", None)
    if not deadline:
        return False
    current = now or utc_now()
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return deadline <= current


def expire_initial_payment_if_due(db, booking, now=None):
    """Mark an unpaid initial request expired without cancelling its booking."""
    if not is_payment_expired(booking, now):
        return False
    status = (booking.payment_status or "pending").lower()
    if status in PAYMENT_IN_PROGRESS_STATUSES:
        return False
    if float(getattr(booking, "amount_paid", 0) or 0) > 0.009:
        return False
    try:
        from app.services.payment_service import PaymentService
        payment_summary = PaymentService.get_payment_summary(booking)
        if float(payment_summary.get("verified_paid") or 0) > 0.009 or float(payment_summary.get("pending_review") or 0) > 0.009:
            return False
    except Exception:
        pass
    if booking.payment_request_status == "expired" and status == "expired":
        return False

    booking.payment_request_status = "expired"
    booking.payment_status = "expired"
    db.add(models.BookingHistory(
        booking_id=booking.id,
        status=booking.status,
        notes="Initial payment request expired; booking retained for caterer review and extension request.",
    ))
    db.commit()
    return True


def booking_is_extension_eligible(booking, now=None):
    current = now or utc_now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    quotation = getattr(booking, "quotation", None)
    if not quotation or quotation.status != "signed":
        return False, "The signed agreement is no longer available."
    if booking.status not in {"awaiting_payment", "pending_payment", "pending"}:
        return False, "This booking is no longer awaiting its initial payment."
    if booking.event_date and booking.event_date < current.astimezone(PHILIPPINE_TIMEZONE).date():
        return False, "The event date has already passed."
    if (booking.payment_status or "").lower() in PAYMENT_IN_PROGRESS_STATUSES:
        return False, "A payment is already submitted, under review, or verified."
    if float(getattr(booking, "amount_paid", 0) or 0) > 0.009:
        return False, "A payment has already been recorded for this booking."
    try:
        from app.services.payment_service import PaymentService
        payment_summary = PaymentService.get_payment_summary(booking)
        if float(payment_summary.get("verified_paid") or 0) > 0.009 or float(payment_summary.get("pending_review") or 0) > 0.009:
            return False, "A payment is already submitted, under review, or verified."
    except Exception:
        pass
    return True, ""

