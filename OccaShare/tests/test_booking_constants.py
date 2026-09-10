import pytest

from app.constants import booking_constants as bc


def test_normalize_payment_status_known():
    assert bc.normalize_payment_status('paid') == 'paid'
    assert bc.normalize_payment_status('fully_paid') == 'paid'
    assert bc.normalize_payment_status('downpayment') == 'deposit_paid'


def test_entry_method_from_source():
    assert bc.entry_method_from_source('Walk-in') == 'walkin'
    assert bc.entry_method_from_source('OccaServe') == 'online'
    assert bc.entry_method_from_source('Internal') == 'internal'
    assert bc.entry_method_from_source(None) == 'online'
