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
        "progress": 40,
        "color": "#b45309",
        "bg": "#fffbeb",
        "emoji": "🟡",
        "booking_status": "preparing",
    },
    {
        "key": "ready_for_delivery",
        "label": "Ready for Delivery / Pickup",
        "progress": 60,
        "color": "#0369a1",
        "bg": "#e0f2fe",
        "emoji": "🔵",
        "booking_status": "ready_for_delivery",
    },
    {
        "key": "setup_in_progress",
        "label": "Setup in Progress",
        "progress": 80,
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
        "booking_status": None,
    },
    {
        "key": "completed",
        "label": "Completed",
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


def build_prep_summary(booking) -> Dict[str, Any]:
    """UI payload for the Preparation status tracker."""
    key = normalize_prep_status(
        getattr(booking, "preparation_status", None),
        getattr(booking, "status", None),
    )
    meta = get_prep_meta(key)
    updated = getattr(booking, "updated_at", None) or getattr(booking, "created_at", None)
    return {
        "status": key,
        "label": meta["label"],
        "progress": meta["progress"],
        "color": meta["color"],
        "bg": meta["bg"],
        "emoji": meta["emoji"],
        "booking_status": getattr(booking, "status", None),
        "last_updated": updated.isoformat() if updated else None,
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
