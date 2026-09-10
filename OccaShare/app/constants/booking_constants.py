"""Booking constants and normalization helpers.

Non-invasive helpers to normalize legacy aliases and provide mapping
between booking_source and an `entry_method` used by UI ('online','walkin','internal','other').
"""
from typing import Optional

# Canonical status values (subset used across the app)
STATUS = {
    'DRAFT': 'draft',
    'PENDING': 'pending',
    'CONFIRMED': 'confirmed',
    'PREPARING': 'preparing',
    'ON_THE_WAY': 'on_the_way',
    'ARRIVED': 'arrived',
    'SETUP_ONGOING': 'setup_ongoing',
    'IN_PROGRESS': 'in_progress',
    'COMPLETED': 'completed',
    'CANCELLED': 'cancelled',
    'EXPIRED': 'expired',
}

# Canonical payment status values
PAYMENT = {
    'PENDING': 'pending',
    'PROOF_SUBMITTED': 'proof_submitted',
    'BALANCE_PROOF_SUBMITTED': 'balance_proof_submitted',
    'REUPLOAD_REQUESTED': 'reupload_requested',
    'DEPOSIT_PAID': 'deposit_paid',
    'PARTIALLY_PAID': 'partially_paid',
    'PAID': 'paid',
    'OVERDUE': 'overdue',
}

# Booking source examples
SOURCE = {
    'OCCASERVE': 'OccaServe',
    'WALKIN': 'Walk-in',
    'FACEBOOK': 'Facebook',
    'PHONE': 'Phone Call',
    'INTERNAL': 'Internal',
    'OTHER': 'Other',
    'OCCASERVE_PLATFORM': 'OccaServe Platform'
}

# Aliases for payment status to canonical PAYMENT values
PAYMENT_ALIAS_MAP = {
    'fully_paid': PAYMENT['PAID'],
    'fully-paid': PAYMENT['PAID'],
    'downpayment_paid': PAYMENT['DEPOSIT_PAID'],
    'downpayment': PAYMENT['DEPOSIT_PAID'],
    'partial_paid': PAYMENT['PARTIALLY_PAID'],
    'partial': PAYMENT['PARTIALLY_PAID'],
    'partially_paid': PAYMENT['PARTIALLY_PAID'],
}

# Coarse mapping from booking_source -> entry method consumed by UI
SOURCE_TO_ENTRY_METHOD = {
    SOURCE['WALKIN']: 'walkin',
    SOURCE['INTERNAL']: 'internal',
    SOURCE['OCCASERVE']: 'online',
    SOURCE['OCCASERVE_PLATFORM']: 'online',
    SOURCE['FACEBOOK']: 'online',
    SOURCE['PHONE']: 'walkin',
    SOURCE['OTHER']: 'other'
}


def normalize_payment_status(value: Optional[str]) -> Optional[str]:
    """Return a canonical payment status for a given value (tolerant).

    This does not mutate DB; it only normalizes representations at the API/UI boundary.
    """
    if not value:
        return None
    v = str(value).strip()
    if v in PAYMENT.values():
        return v
    lower = v.lower()
    if lower in PAYMENT_ALIAS_MAP:
        return PAYMENT_ALIAS_MAP[lower]
    # fallback: return original value
    return v


def entry_method_from_source(source: Optional[str]) -> str:
    """Map a `booking_source` string to an `entry_method`.

    Returns one of: 'online', 'walkin', 'internal', 'other'. Default 'online'.
    """
    if not source:
        return 'online'
    s = str(source).strip()
    return SOURCE_TO_ENTRY_METHOD.get(s, 'online')
