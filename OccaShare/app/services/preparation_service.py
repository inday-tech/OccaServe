"""Simple preparation status tracker helpers for caterer bookings."""

from __future__ import annotations

from typing import Any, Dict, Optional

# Canonical preparation statuses for the Preparation tab
PREP_STATUSES = [
    {
        "key": "not_started",
        "label": "Not Started",
        "progress": 0,
        "color": "#64748b",
        "bg": "#f1f5f9",
        "emoji": "⚪",
        "booking_status": None,
    },
    {
        "key": "preparing",
        "label": "Preparing",
        "progress": 25,
        "color": "#b45309",
        "bg": "#fffbeb",
        "emoji": "🟡",
        "booking_status": "preparing",
    },
    {
        "key": "ready_for_delivery",
        "label": "Preparation Complete",
        "progress": 50,
        "color": "#0369a1",
        "bg": "#e0f2fe",
        "emoji": "🔵",
        "booking_status": "ready_for_delivery",
    },
    {
        "key": "setup_in_progress",
        "label": "Setup in Progress",
        "progress": 75,
        "color": "#c2410c",
        "bg": "#fff7ed",
        "emoji": "🟠",
        "booking_status": "setup_ongoing",
    },
    {
        "key": "ready_for_event",
        "label": "Ready for Event",
        "progress": 90,
        "color": "#7c3aed",
        "bg": "#f5f3ff",
        "emoji": "🟣",
        "booking_status": "ready_for_event",
    },
    {
        "key": "post_event_cleanup",
        "label": "Post-Event Cleanup",
        "progress": 95,
        "color": "#b45309",
        "bg": "#fffbeb",
        "emoji": "🧹",
        "booking_status": None,
    },
    {
        "key": "completed",
        "label": "Event Completed",
        "progress": 100,
        "color": "#166534",
        "bg": "#f0fdf4",
        "emoji": "🟢",
        "booking_status": None,  # full booking completion stays on existing complete flow
    },
]

PREP_STATUS_KEYS = {s["key"] for s in PREP_STATUSES}
PREP_BY_KEY = {s["key"]: s for s in PREP_STATUSES}

# Legacy preparation_status / booking.status → canonical prep key
_ALIAS_MAP = {
    "not_started": "not_started",
    "scheduled": "not_started",
    "in_preparation": "preparing",
    "preparing": "preparing",
    "ready": "ready_for_delivery",
    "ready_for_delivery": "ready_for_delivery",
    "ready_for_pickup": "ready_for_delivery",
    "setup_in_progress": "setup_in_progress",
    "setup_ongoing": "setup_in_progress",
    "ready_for_event": "ready_for_event",
    "arrived": "setup_in_progress",
    "post_event_cleanup": "post_event_cleanup",
    "in_progress": "ready_for_event",
    "completed": "completed",
}


def normalize_prep_status(
    preparation_status: Optional[str] = None,
    booking_status: Optional[str] = None,
) -> str:
    """Resolve a canonical preparation status from booking fields."""
    prep = (preparation_status or "").strip().lower()
    if prep in PREP_STATUS_KEYS:
        return prep
    if prep in _ALIAS_MAP:
        return _ALIAS_MAP[prep]

    bs = (booking_status or "").strip().lower()
    if bs in _ALIAS_MAP:
        return _ALIAS_MAP[bs]
    return "not_started"


def get_prep_meta(status_key: str) -> Dict[str, Any]:
    key = status_key if status_key in PREP_BY_KEY else "not_started"
    return dict(PREP_BY_KEY[key])


def completion_stage_block_reason(booking) -> Optional[str]:
    """Require event cleanup before completing on-site catering bookings."""
    booking_status = (getattr(booking, "status", None) or "").strip().lower()
    document_type = (getattr(booking, "document_type", None) or "").strip().lower()
    if document_type == "invoice" or booking_status == "ready_for_pickup":
        return None

    prep_status = normalize_prep_status(
        getattr(booking, "preparation_status", None),
        booking_status,
    )
    if booking_status not in {"setup_ongoing", "in_progress", "ready_for_event"} or prep_status != "post_event_cleanup":
        return "Complete the Post-Event Cleanup checklist before marking this event completed."
    return None


def build_prep_summary(booking, payment_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """UI payload for the Preparation status tracker."""
    key = normalize_prep_status(
        getattr(booking, "preparation_status", None),
        getattr(booking, "status", None),
    )
    meta = get_prep_meta(key)
    updated = getattr(booking, "preparation_updated_at", None)
    updated_iso = updated.isoformat() if updated else None
    return {
        "status": key,
        "label": meta["label"],
        "progress": meta["progress"],
        "color": meta["color"],
        "bg": meta["bg"],
        "emoji": meta["emoji"],
        "booking_status": getattr(booking, "status", None),
        "preparation_updated_at": updated_iso,
        "last_updated": updated_iso,
        "options": preparation_options(booking, payment_summary),
        "statuses": [
            {
                "key": s["key"],
                "label": s["label"],
                "progress": s["progress"],
                "emoji": s["emoji"],
            }
            for s in PREP_STATUSES
        ],
    }


# ---------------------------------------------------------------------------
# Fulfillment lifecycle: booking.status is derived from preparation_status.
# ---------------------------------------------------------------------------

# Rank of each booking.status inside the fulfillment journey. Pre-fulfillment
# and unknown statuses rank 0 so preparation can never promote them.
BOOKING_STATUS_RANK = {
    "tentative": 1,
    "confirmed": 1,
    "paid": 1,
    "preparing": 2,
    "ready_for_delivery": 3,
    "ready_for_pickup": 3,
    "on_the_way": 4,
    "arrived": 5,
    "setup_ongoing": 6,
    "setup_in_progress": 6,
    "in_progress": 6,
    "ready_for_event": 7,
    "post_event_cleanup": 8,
    "completed": 9,
    "delivered": 9,
}

TERMINAL_BOOKING_STATUSES = {
    "completed", "delivered", "cancelled", "rejected", "expired", "no_show", "released",
}

# booking.status values that allow the preparation tracker to be used.
PREP_ACCEPTED_BOOKING_STATUSES = {
    "confirmed", "preparing", "ready_for_delivery", "ready_for_pickup",
    "on_the_way", "arrived", "setup_ongoing", "in_progress", "ready_for_event",
}

# Canonical preparation key -> booking.status it implies for display/sync.
# Legacy raw preparation_status values are resolved through _ALIAS_MAP first.
_PREP_KEY_TO_BOOKING_STATUS = {
    "preparing": "preparing",
    "ready_for_delivery": "ready_for_delivery",
    "setup_in_progress": "setup_ongoing",
    "ready_for_event": "ready_for_event",
    "post_event_cleanup": "post_event_cleanup",
    "completed": "completed",
}

# Legacy preparation_status values that map to a booking.status directly
# (checked before alias normalization so e.g. "arrived" stays "arrived").
_LEGACY_PREP_TO_BOOKING_STATUS = {
    "ready_for_pickup": "ready_for_pickup",
    "setup_ongoing": "setup_ongoing",
    "arrived": "arrived",
    "on_the_way": "on_the_way",
    "in_progress": "in_progress",
}


def booking_status_rank(status: Optional[str]) -> int:
    return BOOKING_STATUS_RANK.get((status or "").strip().lower(), 0)


def canonical_prep_key(raw_status: Optional[str]) -> Optional[str]:
    """Resolve a raw preparation_status value to a canonical PREP_STATUSES key.

    Unlike normalize_prep_status, this never falls back to booking.status.
    """
    value = (raw_status or "").strip().lower()
    if value in PREP_BY_KEY:
        return value
    return _ALIAS_MAP.get(value)


def derive_booking_status(status: Optional[str], preparation_status: Optional[str] = "") -> str:
    """Return the effective booking.status for display.

    preparation_status is the source of truth for fulfillment: when the
    preparation stage is further along than booking.status, the derived
    (further) status wins. booking.status is never moved backward and
    pre-fulfillment/terminal statuses are never overridden.
    """
    bs = (status or "").strip().lower()
    if not bs:
        return bs
    prep = (preparation_status or "").strip().lower()
    candidate = None
    if prep:
        if prep in _PREP_KEY_TO_BOOKING_STATUS:
            candidate = _PREP_KEY_TO_BOOKING_STATUS[prep]
        elif prep in _LEGACY_PREP_TO_BOOKING_STATUS:
            candidate = _LEGACY_PREP_TO_BOOKING_STATUS[prep]
        else:
            canonical = _ALIAS_MAP.get(prep)
            if canonical:
                candidate = _PREP_KEY_TO_BOOKING_STATUS.get(canonical)
    bs_rank = BOOKING_STATUS_RANK.get(bs)
    if candidate is None or bs_rank is None:
        return bs
    return candidate if BOOKING_STATUS_RANK.get(candidate, 0) > bs_rank else bs


def sync_booking_status_from_preparation(booking) -> bool:
    """Advance booking.status to the stage implied by preparation_status.

    Only promotes (never regresses, never overrides terminal or
    pre-fulfillment statuses). Returns True when booking.status changed.
    """
    bs = (getattr(booking, "status", None) or "").strip().lower()
    if bs in TERMINAL_BOOKING_STATUSES or booking_status_rank(bs) < 1:
        return False
    prep_key = canonical_prep_key(getattr(booking, "preparation_status", None))
    if not prep_key:
        return False
    target = PREP_BY_KEY[prep_key].get("booking_status")
    if not target or BOOKING_STATUS_RANK.get(target, 0) <= booking_status_rank(bs):
        return False
    booking.status = target
    return True


def preparation_transition_error(
    booking,
    new_key: str,
    payment_summary: Optional[Dict[str, Any]] = None,
    has_pending_cancellation: bool = False,
) -> Optional[tuple]:
    """Single source of truth for preparation-status transition rules.

    Returns (http_status_code, detail) when the transition is not allowed,
    or None when it is allowed. The caller still enforces request-level
    concerns such as checklist_confirmed.
    """
    booking_status = (getattr(booking, "status", None) or "").strip().lower()
    if getattr(booking, "is_archived", False) or booking_status in {
        "cancelled", "expired", "completed", "delivered", "rejected", "no_show",
    }:
        return (400, "Cannot update preparation on this booking.")
    if has_pending_cancellation:
        return (409, "Resolve the pending customer cancellation request before updating preparation.")
    if booking_status not in PREP_ACCEPTED_BOOKING_STATUSES:
        return (409, "Accept the booking before updating its preparation status.")
    if new_key not in PREP_STATUS_KEYS:
        return (400, "Invalid preparation status. Choose one of the available options.")
    if new_key == "ready_for_delivery":
        return (409, "Upload dispatch proof from the preparation checklist before marking the booking ready for delivery.")
    if new_key == "completed":
        return (409, "Use the booking completion action after post-event cleanup and full payment verification.")

    old_key = normalize_prep_status(
        getattr(booking, "preparation_status", None), booking_status
    )
    if old_key == new_key:
        return None

    order = [status["key"] for status in PREP_STATUSES]
    old_index = order.index(old_key)
    new_index = order.index(new_key)
    if new_index < old_index:
        return (400, "Preparation status cannot move backward. Choose the current or next stage.")
    if new_index > old_index + 1:
        return (409, "Complete the current preparation stage before moving to the next one.")

    if new_key == "preparing" and payment_summary is not None and not payment_summary.get("can_start_preparation"):
        return (409, "Verify the required downpayment before starting preparation.")
    if new_key == "setup_in_progress" and (
        old_key != "ready_for_delivery" or booking_status != "arrived"
    ):
        return (409, "Mark the booking as arrived at the venue before starting setup.")
    if new_key == "ready_for_event" and (
        old_key != "setup_in_progress" or booking_status not in {"setup_ongoing", "in_progress"}
    ):
        return (409, "Start and complete venue setup before marking the event ready.")
    if new_key == "post_event_cleanup" and (
        old_key != "ready_for_event" or booking_status not in {"setup_ongoing", "in_progress", "ready_for_event"}
    ):
        return (409, "Mark the event ready and finish the service before starting post-event cleanup.")
    return None


def preparation_options(booking, payment_summary: Optional[Dict[str, Any]] = None) -> list:
    """Backend-computed allowed preparation transitions for the UI.

    Each option mirrors what POST /preparation-status would accept, so the
    frontend does not need to duplicate the transition rules.
    """
    options = []
    for status in PREP_STATUSES:
        error = preparation_transition_error(booking, status["key"], payment_summary)
        options.append({
            "key": status["key"],
            "label": status["label"],
            "progress": status["progress"],
            "emoji": status["emoji"],
            "color": status["color"],
            "bg": status["bg"],
            "allowed": error is None,
            "reason": "" if error is None else error[1],
        })
    return options
